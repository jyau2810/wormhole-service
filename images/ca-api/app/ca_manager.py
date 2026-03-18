from __future__ import annotations

import ipaddress
import json
import re
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509 import NameOID
from cryptography.x509.oid import ExtendedKeyUsageOID

from .settings import Settings


def utcnow() -> datetime:
    return datetime.now(UTC)


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    return cleaned.strip("-")[:40] or "device"


def _pem_private_key(key: rsa.RSAPrivateKey) -> bytes:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _pem_certificate(cert: x509.Certificate) -> bytes:
    return cert.public_bytes(serialization.Encoding.PEM)


@dataclass
class IssuedBundle:
    serial: str
    subject: str
    bundle_filename: str
    p12_password_hint: str


class CAManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_dir = settings.data_dir
        self.ca_dir = self.base_dir / "ca"
        self.server_dir = self.base_dir / "server"
        self.clients_dir = self.base_dir / "clients"
        self.meta_path = self.base_dir / "metadata.json"
        self.lock = threading.Lock()
        self._ensure_directories()
        self._ensure_materials()

    def _ensure_directories(self) -> None:
        for path in (self.base_dir, self.ca_dir, self.server_dir, self.clients_dir):
            path.mkdir(parents=True, exist_ok=True)

    @property
    def ca_key_path(self) -> Path:
        return self.ca_dir / "ca-key.pem"

    @property
    def ca_cert_path(self) -> Path:
        return self.ca_dir / "ca-cert.pem"

    @property
    def crl_path(self) -> Path:
        return self.ca_dir / "crl.pem"

    @property
    def server_key_path(self) -> Path:
        return self.server_dir / "server-key.pem"

    @property
    def server_cert_path(self) -> Path:
        return self.server_dir / "server-cert.pem"

    def _load_metadata(self) -> dict:
        if not self.meta_path.exists():
            return {"certificates": {}}
        return json.loads(self.meta_path.read_text(encoding="utf-8"))

    def _save_metadata(self, payload: dict) -> None:
        self.meta_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _load_private_key(self, path: Path):
        return serialization.load_pem_private_key(path.read_bytes(), password=None)

    def _load_certificate(self, path: Path) -> x509.Certificate:
        return x509.load_pem_x509_certificate(path.read_bytes())

    def _ensure_materials(self) -> None:
        with self.lock:
            if not self.ca_key_path.exists() or not self.ca_cert_path.exists():
                self._generate_ca()
            if not self.server_key_path.exists() or not self.server_cert_path.exists():
                self._generate_server_certificate()
            if not self.crl_path.exists():
                self._write_crl()
            if not self.meta_path.exists():
                self._save_metadata({"certificates": {}})

    def _generate_ca(self) -> None:
        now = utcnow()
        key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
        subject = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, self.settings.ca_common_name),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.settings.ca_organization),
            ]
        )
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=self.settings.ca_validity_days))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=True,
                    crl_sign=True,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(private_key=key, algorithm=hashes.SHA256())
        )
        self.ca_key_path.write_bytes(_pem_private_key(key))
        self.ca_cert_path.write_bytes(_pem_certificate(cert))

    def _subject_alt_names(self) -> x509.SubjectAlternativeName:
        names: list[x509.GeneralName] = []
        for value in [self.settings.vpn_server_host, *self.settings.vpn_server_alt_names]:
            if not value:
                continue
            try:
                names.append(x509.IPAddress(ipaddress.ip_address(value)))
            except ValueError:
                names.append(x509.DNSName(value))
        return x509.SubjectAlternativeName(names)

    def _generate_server_certificate(self) -> None:
        ca_key = self._load_private_key(self.ca_key_path)
        ca_cert = self._load_certificate(self.ca_cert_path)
        now = utcnow()
        key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
        subject = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, self.settings.vpn_server_host),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.settings.ca_organization),
            ]
        )
        cert_builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(ca_cert.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=self.settings.server_cert_validity_days))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
                critical=False,
            )
            .add_extension(self._subject_alt_names(), critical=False)
        )
        cert = cert_builder.sign(private_key=ca_key, algorithm=hashes.SHA256())
        self.server_key_path.write_bytes(_pem_private_key(key))
        self.server_cert_path.write_bytes(_pem_certificate(cert))

    def _write_crl(self) -> None:
        ca_key = self._load_private_key(self.ca_key_path)
        ca_cert = self._load_certificate(self.ca_cert_path)
        payload = self._load_metadata()
        now = utcnow()
        builder = (
            x509.CertificateRevocationListBuilder()
            .issuer_name(ca_cert.subject)
            .last_update(now - timedelta(minutes=5))
            .next_update(now + timedelta(days=7))
        )
        for item in payload.get("certificates", {}).values():
            if item.get("status") != "revoked":
                continue
            revoked_at = datetime.fromisoformat(item["revoked_at"])
            revoked = (
                x509.RevokedCertificateBuilder()
                .serial_number(int(item["serial"], 16))
                .revocation_date(revoked_at)
                .build()
            )
            builder = builder.add_revoked_certificate(revoked)
        crl = builder.sign(private_key=ca_key, algorithm=hashes.SHA256())
        self.crl_path.write_bytes(crl.public_bytes(serialization.Encoding.PEM))

    def health(self) -> dict:
        return {
            "ca_cert": self.ca_cert_path.exists(),
            "server_cert": self.server_cert_path.exists(),
            "crl": self.crl_path.exists(),
        }

    def issue_client_certificate(self, username: str, slot_no: int, device_label: str) -> IssuedBundle:
        with self.lock:
            ca_key = self._load_private_key(self.ca_key_path)
            ca_cert = self._load_certificate(self.ca_cert_path)
            now = utcnow()
            serial_int = x509.random_serial_number()
            serial_hex = format(serial_int, "x")
            safe_label = _slug(device_label)
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            subject = x509.Name(
                [
                    x509.NameAttribute(NameOID.COMMON_NAME, safe_label),
                    x509.NameAttribute(NameOID.USER_ID, username),
                    x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, f"slot-{slot_no}"),
                ]
            )
            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(ca_cert.subject)
                .public_key(key.public_key())
                .serial_number(serial_int)
                .not_valid_before(now - timedelta(minutes=5))
                .not_valid_after(now + timedelta(days=self.settings.client_cert_validity_days))
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .add_extension(
                    x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),
                    critical=False,
                )
                .sign(private_key=ca_key, algorithm=hashes.SHA256())
            )

            export_password = self.settings.p12_export_password.encode("utf-8")
            if export_password:
                encryption = serialization.BestAvailableEncryption(export_password)
                password_hint = "configured in P12_EXPORT_PASSWORD"
            else:
                encryption = serialization.NoEncryption()
                password_hint = "none"

            p12_blob = pkcs12.serialize_key_and_certificates(
                name=f"{username}-slot-{slot_no}".encode("utf-8"),
                key=key,
                cert=cert,
                cas=[ca_cert],
                encryption_algorithm=encryption,
            )

            serial_dir = self.clients_dir / serial_hex
            serial_dir.mkdir(parents=True, exist_ok=True)
            (serial_dir / "client-key.pem").write_bytes(_pem_private_key(key))
            (serial_dir / "client-cert.pem").write_bytes(_pem_certificate(cert))
            (serial_dir / "client.p12").write_bytes(p12_blob)
            bundle_filename = f"{username}-slot-{slot_no}-{safe_label}.zip"
            bundle_path = serial_dir / bundle_filename
            readme = (
                "Import client.p12 into your OpenConnect-compatible client.\n"
                f"PKCS#12 password: {password_hint}\n"
                f"Username: {username}\n"
                "Password: use the VPN account password configured in the admin portal.\n"
            ).encode("utf-8")
            with ZipFile(bundle_path, "w", compression=ZIP_DEFLATED) as archive:
                archive.writestr("client.p12", p12_blob)
                archive.writestr("client-cert.pem", _pem_certificate(cert))
                archive.writestr("client-key.pem", _pem_private_key(key))
                archive.writestr("ca-cert.pem", self.ca_cert_path.read_bytes())
                archive.writestr("README.txt", readme)

            payload = self._load_metadata()
            payload.setdefault("certificates", {})[serial_hex] = {
                "serial": serial_hex,
                "username": username,
                "slot_no": slot_no,
                "device_label": device_label,
                "subject": cert.subject.rfc4514_string(),
                "bundle_filename": bundle_filename,
                "status": "active",
                "issued_at": now.isoformat(),
                "revoked_at": None,
            }
            self._save_metadata(payload)
            return IssuedBundle(
                serial=serial_hex,
                subject=cert.subject.rfc4514_string(),
                bundle_filename=bundle_filename,
                p12_password_hint=password_hint,
            )

    def revoke_certificate(self, serial: str) -> None:
        with self.lock:
            payload = self._load_metadata()
            item = payload.get("certificates", {}).get(serial)
            if item is None:
                raise KeyError(serial)
            if item.get("status") == "revoked":
                return
            item["status"] = "revoked"
            item["revoked_at"] = utcnow().isoformat()
            self._save_metadata(payload)
            self._write_crl()

    def bundle_bytes(self, serial: str) -> tuple[str, bytes]:
        payload = self._load_metadata()
        item = payload.get("certificates", {}).get(serial)
        if item is None:
            raise KeyError(serial)
        bundle_path = self.clients_dir / serial / item["bundle_filename"]
        return item["bundle_filename"], bundle_path.read_bytes()

