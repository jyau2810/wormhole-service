from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel

from .ca_manager import CAManager
from .logging_setup import configure_logging, request_id_var
from .settings import Settings, load_settings

settings: Settings = load_settings()
configure_logging(settings)

logger = logging.getLogger("wormhole.app")
access_logger = logging.getLogger("wormhole.access")

manager = CAManager(settings)
app = FastAPI(title="wormhole-ca-api")


class IssueRequest(BaseModel):
    username: str
    slot_no: int
    device_label: str


class RevokeRequest(BaseModel):
    serial: str


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", uuid4().hex[:12])
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.exception(
            "request_failed method=%s path=%s duration_ms=%s",
            request.method,
            request.url.path,
            duration_ms,
        )
        request_id_var.reset(token)
        raise
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    access_logger.info(
        "method=%s path=%s status_code=%s duration_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    response.headers["x-request-id"] = request_id
    request_id_var.reset(token)
    return response


def verify_token(authorization: str = Header(default="")) -> None:
    expected = f"Bearer {settings.token}"
    if not settings.token or authorization != expected:
        logger.warning("authorization_failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


@app.on_event("startup")
def startup() -> None:
    logger.info("startup_complete")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", **manager.health()}


@app.post("/internal/certificates/issue", dependencies=[Depends(verify_token)])
def issue_certificate(payload: IssueRequest) -> dict:
    bundle = manager.issue_client_certificate(
        username=payload.username,
        slot_no=payload.slot_no,
        device_label=payload.device_label,
    )
    logger.info(
        "certificate_issued username=%s slot_no=%s device_label=%s serial=%s",
        payload.username,
        payload.slot_no,
        payload.device_label,
        bundle.serial,
    )
    return {
        "serial": bundle.serial,
        "subject": bundle.subject,
        "bundle_filename": bundle.bundle_filename,
        "p12_password_hint": bundle.p12_password_hint,
    }


@app.post("/internal/certificates/revoke", dependencies=[Depends(verify_token)])
def revoke_certificate(payload: RevokeRequest) -> dict:
    try:
        manager.revoke_certificate(payload.serial)
    except KeyError as exc:
        logger.warning("certificate_revoke_missing serial=%s", payload.serial)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="certificate not found") from exc
    logger.info("certificate_revoked serial=%s", payload.serial)
    return {"status": "revoked"}


@app.get("/internal/certificates/{serial}/bundle", dependencies=[Depends(verify_token)])
def download_bundle(serial: str) -> Response:
    try:
        filename, payload = manager.bundle_bytes(serial)
    except KeyError as exc:
        logger.warning("certificate_bundle_missing serial=%s", serial)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="bundle not found") from exc
    logger.info("certificate_bundle_downloaded serial=%s filename=%s", serial, filename)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=payload, media_type="application/zip", headers=headers)

