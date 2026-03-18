from __future__ import annotations

import httpx

from .settings import Settings


class CAClient:
    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.ca_api_url.rstrip("/")
        self.token = settings.ca_api_token

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def issue_certificate(self, username: str, slot_no: int, device_label: str) -> dict:
        response = httpx.post(
            f"{self.base_url}/internal/certificates/issue",
            headers=self.headers,
            json={
                "username": username,
                "slot_no": slot_no,
                "device_label": device_label,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def revoke_certificate(self, serial: str) -> None:
        response = httpx.post(
            f"{self.base_url}/internal/certificates/revoke",
            headers=self.headers,
            json={"serial": serial},
            timeout=30.0,
        )
        response.raise_for_status()

    def download_bundle(self, serial: str) -> tuple[str, bytes]:
        response = httpx.get(
            f"{self.base_url}/internal/certificates/{serial}/bundle",
            headers=self.headers,
            timeout=30.0,
        )
        response.raise_for_status()
        disposition = response.headers.get("content-disposition", "")
        filename = "client-bundle.zip"
        if "filename=" in disposition:
            filename = disposition.split("filename=")[-1].strip('"')
        return filename, response.content

