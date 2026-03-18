from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .ca_client import CAClient
from .db import transaction, wait_for_db
from .logging_setup import configure_logging, request_id_var
from .radius_sync import (
    effective_radius_expiration,
    format_radius_expiration,
    hash_vpn_password,
    next_available_slot,
    to_utc_naive_end_of_day,
)
from .security import hash_admin_password, verify_admin_password
from .settings import Settings, load_settings

settings: Settings = load_settings()
configure_logging(settings)

logger = logging.getLogger("wormhole.app")
access_logger = logging.getLogger("wormhole.access")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app = FastAPI(title="wormhole-admin-portal")
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret, same_site="lax")
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
ca_client = CAClient(settings)
LOCAL_ZONE = ZoneInfo(settings.timezone_name)


def flash(request: Request, level: str, text: str) -> None:
    request.session["flash"] = {"level": level, "text": text}


def take_flash(request: Request) -> dict[str, str] | None:
    return request.session.pop("flash", None)


def current_admin(request: Request) -> str | None:
    return request.session.get("admin_username")


def require_login(request: Request) -> RedirectResponse | None:
    if current_admin(request):
        return None
    return RedirectResponse(url="/login", status_code=303)


def localize(value: datetime | None) -> str:
    if value is None:
        return "-"
    aware = value.replace(tzinfo=UTC).astimezone(LOCAL_ZONE)
    return aware.strftime("%Y-%m-%d %H:%M:%S")


templates.env.filters["datetime_local"] = localize


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", uuid4().hex[:12])
    request.state.request_id = request_id
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


def sync_radius_rows(cursor, username: str, password_hash: str, status: str, expiration_at: datetime) -> None:
    cursor.execute(
        "DELETE FROM radcheck WHERE username = %s AND attribute IN ('Crypt-Password', 'Expiration')",
        (username,),
    )
    effective = effective_radius_expiration(status, expiration_at)
    cursor.executemany(
        "INSERT INTO radcheck (username, attribute, op, value) VALUES (%s, %s, ':=', %s)",
        [
            (username, "Crypt-Password", password_hash),
            (username, "Expiration", format_radius_expiration(effective)),
        ],
    )


def bootstrap_admin() -> None:
    with transaction(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM admin_users WHERE username = %s", (settings.admin_username,))
            row = cursor.fetchone()
            password_hash = hash_admin_password(settings.admin_password)
            if row:
                cursor.execute(
                    "UPDATE admin_users SET password_hash = %s WHERE id = %s",
                    (password_hash, row["id"]),
                )
                logger.info("bootstrap_admin_updated username=%s", settings.admin_username)
            else:
                cursor.execute(
                    "INSERT INTO admin_users (username, password_hash) VALUES (%s, %s)",
                    (settings.admin_username, password_hash),
                )
                logger.info("bootstrap_admin_created username=%s", settings.admin_username)


def load_dashboard_accounts():
    with transaction(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.*,
                    (
                        SELECT COUNT(*)
                        FROM vpn_devices d
                        WHERE d.account_id = a.id AND d.cert_status = 'active'
                    ) AS active_devices,
                    (
                        SELECT MAX(authdate)
                        FROM radpostauth p
                        WHERE p.username = a.username AND p.reply = 'Access-Accept'
                    ) AS last_success_at,
                    (
                        SELECT COUNT(*)
                        FROM radacct r
                        WHERE r.username = a.username AND r.acctstoptime IS NULL
                    ) AS active_sessions
                FROM vpn_accounts a
                ORDER BY a.created_at DESC
                """
            )
            return cursor.fetchall()


def load_account_detail(account_id: int):
    with transaction(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.*,
                    (
                        SELECT COUNT(*)
                        FROM vpn_devices d
                        WHERE d.account_id = a.id AND d.cert_status = 'active'
                    ) AS active_devices,
                    (
                        SELECT MAX(authdate)
                        FROM radpostauth p
                        WHERE p.username = a.username AND p.reply = 'Access-Accept'
                    ) AS last_success_at,
                    (
                        SELECT COUNT(*)
                        FROM radacct r
                        WHERE r.username = a.username AND r.acctstoptime IS NULL
                    ) AS active_sessions
                FROM vpn_accounts a
                WHERE a.id = %s
                """,
                (account_id,),
            )
            account = cursor.fetchone()
            if not account:
                return None
            cursor.execute(
                """
                SELECT *
                FROM vpn_devices
                WHERE account_id = %s
                ORDER BY cert_status = 'active' DESC, created_at DESC
                """,
                (account_id,),
            )
            devices = cursor.fetchall()
            cursor.execute(
                """
                SELECT username, reply, authdate
                FROM radpostauth
                WHERE username = %s
                ORDER BY authdate DESC
                LIMIT 20
                """,
                (account["username"],),
            )
            auth_logs = cursor.fetchall()
            cursor.execute(
                """
                SELECT acctstarttime, framedipaddress, callingstationid, acctinputoctets, acctoutputoctets
                FROM radacct
                WHERE username = %s AND acctstoptime IS NULL
                ORDER BY acctstarttime DESC
                """,
                (account["username"],),
            )
            active_sessions = cursor.fetchall()
            return {
                "account": account,
                "devices": devices,
                "auth_logs": auth_logs,
                "active_sessions": active_sessions,
            }


def parse_account_date(date_value: str) -> datetime:
    return to_utc_naive_end_of_day(date_value, settings.timezone_name)


@app.on_event("startup")
def startup() -> None:
    logger.info("startup_begin")
    wait_for_db(settings)
    bootstrap_admin()
    logger.info("startup_complete")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    if current_admin(request):
        return RedirectResponse(url="/accounts", status_code=303)
    return RedirectResponse(url="/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if current_admin(request):
        return RedirectResponse(url="/accounts", status_code=303)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "flash": take_flash(request)},
    )


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    with transaction(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM admin_users WHERE username = %s", (username,))
            row = cursor.fetchone()
    if not row or not verify_admin_password(row["password_hash"], password):
        logger.warning("admin_login_failed username=%s", username)
        flash(request, "error", "Invalid credentials.")
        return RedirectResponse(url="/login", status_code=303)
    request.session["admin_username"] = row["username"]
    logger.info("admin_login_succeeded username=%s", row["username"])
    flash(request, "success", "Logged in.")
    return RedirectResponse(url="/accounts", status_code=303)


@app.post("/logout")
def logout(request: Request):
    username = current_admin(request)
    request.session.clear()
    logger.info("admin_logout username=%s", username or "-")
    flash(request, "success", "Logged out.")
    return RedirectResponse(url="/login", status_code=303)


@app.get("/accounts", response_class=HTMLResponse)
def account_list(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        "accounts.html",
        {
            "request": request,
            "accounts": load_dashboard_accounts(),
            "flash": take_flash(request),
            "current_admin": current_admin(request),
            "today": datetime.now(LOCAL_ZONE).date().isoformat(),
        },
    )


@app.post("/accounts")
def create_account(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    expiration_date: str = Form(...),
):
    redirect = require_login(request)
    if redirect:
        return redirect
    password_hash = hash_vpn_password(password)
    expiration_at = parse_account_date(expiration_date)
    try:
        with transaction(settings) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO vpn_accounts (username, password_hash, status, expiration_at, max_device_slots)
                    VALUES (%s, %s, 'enabled', %s, 2)
                    """,
                    (username, password_hash, expiration_at),
                )
                sync_radius_rows(cursor, username, password_hash, "enabled", expiration_at)
    except Exception:
        logger.exception("account_create_failed username=%s", username)
        flash(request, "error", f"Failed to create account: {username}")
        return RedirectResponse(url="/accounts", status_code=303)
    logger.info("account_created username=%s expiration_at=%s", username, expiration_at.isoformat())
    flash(request, "success", f"Account {username} created.")
    return RedirectResponse(url="/accounts", status_code=303)


@app.get("/accounts/{account_id}", response_class=HTMLResponse)
def account_detail(request: Request, account_id: int):
    redirect = require_login(request)
    if redirect:
        return redirect
    payload = load_account_detail(account_id)
    if payload is None:
        logger.warning("account_detail_missing account_id=%s", account_id)
        flash(request, "error", "Account not found.")
        return RedirectResponse(url="/accounts", status_code=303)
    return templates.TemplateResponse(
        "account_detail.html",
        {
            "request": request,
            **payload,
            "flash": take_flash(request),
            "current_admin": current_admin(request),
            "today": datetime.now(LOCAL_ZONE).date().isoformat(),
            "p12_password_hint": settings.p12_export_password or "none",
        },
    )


@app.post("/accounts/{account_id}/extend")
def extend_account(request: Request, account_id: int, expiration_date: str = Form(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    expiration_at = parse_account_date(expiration_date)
    try:
        with transaction(settings) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM vpn_accounts WHERE id = %s", (account_id,))
                account = cursor.fetchone()
                if not account:
                    flash(request, "error", "Account not found.")
                    return RedirectResponse(url="/accounts", status_code=303)
                cursor.execute(
                    "UPDATE vpn_accounts SET expiration_at = %s WHERE id = %s",
                    (expiration_at, account_id),
                )
                sync_radius_rows(
                    cursor,
                    account["username"],
                    account["password_hash"],
                    account["status"],
                    expiration_at,
                )
    except Exception:
        logger.exception("account_extend_failed account_id=%s", account_id)
        flash(request, "error", "Failed to update expiration.")
        return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)
    logger.info("account_extended username=%s expiration_at=%s", account["username"], expiration_at.isoformat())
    flash(request, "success", "Expiration updated.")
    return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)


@app.post("/accounts/{account_id}/toggle")
def toggle_account(request: Request, account_id: int):
    redirect = require_login(request)
    if redirect:
        return redirect
    try:
        with transaction(settings) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM vpn_accounts WHERE id = %s", (account_id,))
                account = cursor.fetchone()
                if not account:
                    flash(request, "error", "Account not found.")
                    return RedirectResponse(url="/accounts", status_code=303)
                new_status = "disabled" if account["status"] == "enabled" else "enabled"
                cursor.execute(
                    "UPDATE vpn_accounts SET status = %s WHERE id = %s",
                    (new_status, account_id),
                )
                sync_radius_rows(
                    cursor,
                    account["username"],
                    account["password_hash"],
                    new_status,
                    account["expiration_at"],
                )
    except Exception:
        logger.exception("account_toggle_failed account_id=%s", account_id)
        flash(request, "error", "Failed to update account status.")
        return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)
    logger.info("account_toggled username=%s status=%s", account["username"], new_status)
    flash(request, "success", f"Account {new_status}.")
    return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)


@app.post("/accounts/{account_id}/password")
def rotate_password(request: Request, account_id: int, password: str = Form(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    password_hash = hash_vpn_password(password)
    try:
        with transaction(settings) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM vpn_accounts WHERE id = %s", (account_id,))
                account = cursor.fetchone()
                if not account:
                    flash(request, "error", "Account not found.")
                    return RedirectResponse(url="/accounts", status_code=303)
                cursor.execute(
                    "UPDATE vpn_accounts SET password_hash = %s WHERE id = %s",
                    (password_hash, account_id),
                )
                sync_radius_rows(
                    cursor,
                    account["username"],
                    password_hash,
                    account["status"],
                    account["expiration_at"],
                )
    except Exception:
        logger.exception("account_password_rotate_failed account_id=%s", account_id)
        flash(request, "error", "Failed to rotate VPN password.")
        return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)
    logger.info("account_password_rotated username=%s", account["username"])
    flash(request, "success", "VPN password updated.")
    return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)


@app.post("/accounts/{account_id}/devices")
def issue_device(request: Request, account_id: int, device_label: str = Form(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    try:
        with transaction(settings) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM vpn_accounts WHERE id = %s", (account_id,))
                account = cursor.fetchone()
                if not account:
                    flash(request, "error", "Account not found.")
                    return RedirectResponse(url="/accounts", status_code=303)
                cursor.execute(
                    "SELECT slot_no FROM vpn_devices WHERE account_id = %s AND cert_status = 'active'",
                    (account_id,),
                )
                active_slots = {row["slot_no"] for row in cursor.fetchall()}
                slot_no = next_available_slot(active_slots, account["max_device_slots"])
                if slot_no is None:
                    logger.warning("device_issue_rejected username=%s reason=max_slots", account["username"])
                    flash(request, "error", "All 2 device slots are already occupied.")
                    return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)
                bundle = ca_client.issue_certificate(account["username"], slot_no, device_label)
                cursor.execute(
                    """
                    INSERT INTO vpn_devices
                        (account_id, slot_no, device_label, cert_serial, cert_subject, bundle_filename, cert_status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'active')
                    """,
                    (
                        account_id,
                        slot_no,
                        device_label,
                        bundle["serial"],
                        bundle["subject"],
                        bundle["bundle_filename"],
                    ),
                )
    except Exception:
        logger.exception("device_issue_failed account_id=%s device_label=%s", account_id, device_label)
        flash(request, "error", "Failed to issue device certificate.")
        return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)
    logger.info(
        "device_issued username=%s slot_no=%s device_label=%s cert_serial=%s",
        account["username"],
        slot_no,
        device_label,
        bundle["serial"],
    )
    flash(request, "success", f"Device issued in slot {slot_no}. Download the bundle below.")
    return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)


@app.get("/devices/{device_id}/bundle")
def download_device_bundle(request: Request, device_id: int):
    redirect = require_login(request)
    if redirect:
        return redirect
    with transaction(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT d.*, a.id AS account_id, a.username
                FROM vpn_devices d
                JOIN vpn_accounts a ON a.id = d.account_id
                WHERE d.id = %s
                """,
                (device_id,),
            )
            device = cursor.fetchone()
    if not device:
        logger.warning("device_bundle_missing device_id=%s", device_id)
        flash(request, "error", "Device not found.")
        return RedirectResponse(url="/accounts", status_code=303)
    try:
        filename, payload = ca_client.download_bundle(device["cert_serial"])
    except Exception:
        logger.exception("device_bundle_download_failed device_id=%s cert_serial=%s", device_id, device["cert_serial"])
        flash(request, "error", "Failed to download bundle.")
        return RedirectResponse(url=f"/accounts/{device['account_id']}", status_code=303)
    logger.info("device_bundle_downloaded username=%s device_id=%s", device["username"], device_id)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=payload, media_type="application/zip", headers=headers)


@app.post("/devices/{device_id}/revoke")
def revoke_device(request: Request, device_id: int):
    redirect = require_login(request)
    if redirect:
        return redirect
    try:
        with transaction(settings) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT d.*, a.id AS account_id, a.username
                    FROM vpn_devices d
                    JOIN vpn_accounts a ON a.id = d.account_id
                    WHERE d.id = %s
                    """,
                    (device_id,),
                )
                device = cursor.fetchone()
                if not device:
                    flash(request, "error", "Device not found.")
                    return RedirectResponse(url="/accounts", status_code=303)
                ca_client.revoke_certificate(device["cert_serial"])
                cursor.execute(
                    """
                    UPDATE vpn_devices
                    SET cert_status = 'revoked', revoked_at = UTC_TIMESTAMP()
                    WHERE id = %s
                    """,
                    (device_id,),
                )
    except Exception:
        logger.exception("device_revoke_failed device_id=%s", device_id)
        flash(request, "error", "Failed to revoke device.")
        return RedirectResponse(url="/accounts", status_code=303)
    logger.info("device_revoked username=%s device_id=%s cert_serial=%s", device["username"], device_id, device["cert_serial"])
    flash(request, "success", "Device revoked and slot released.")
    return RedirectResponse(url=f"/accounts/{device['account_id']}", status_code=303)

