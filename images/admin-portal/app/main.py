from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .analytics import refresh_account_events
from .ca_client import CAClient
from .connection_config import build_connection_config
from .db import transaction, wait_for_db
from .logging_setup import configure_logging, request_id_var
from .macos_installer import build_macos_installer_archive
from .ocserv_policy import sync_ocserv_user_policy, validate_ocserv_username
from .radius_sync import radius_check_rows, to_utc_naive_end_of_day
from .schema import ensure_admin_schema
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
    aware = value.replace(tzinfo=timezone.utc).astimezone(LOCAL_ZONE)
    return aware.strftime("%Y-%m-%d %H:%M:%S")


def pretty_event_type(value: str) -> str:
    return value.replace("_", " ").title()


templates.env.filters["datetime_local"] = localize
templates.env.filters["event_name"] = pretty_event_type


DEFAULT_SPEED_PROFILES = (
    ("starter-2m", "Starter 2M", 2048, 2048),
    ("standard-10m", "Standard 10M", 10240, 10240),
    ("power-50m", "Power 50M", 51200, 51200),
)

PLATFORM_GUIDES = {
    "macos": {
        "title": "macOS",
        "steps": [
            "打开系统设置，进入网络，新增 VPN 配置，类型选择 L2TP over IPSec。",
            "服务器地址使用下方接入点列表中的地址，账号和密码使用本系统中的 VPN 账号。",
            "共享密钥使用后台展示的 VPN Shared PSK。",
            "在高级选项中勾选通过 VPN 发送所有流量，然后保存并连接。",
        ],
    },
    "windows": {
        "title": "Windows",
        "steps": [
            "进入设置中的 VPN 页面，新增 L2TP/IPSec VPN。",
            "服务器地址与账号密码使用后台连接配置页展示的参数。",
            "高级设置里填写预共享密钥，并把安全协议调整为允许 MS-CHAP v2。",
            "如果系统提示 IPSec 受限，需要按企业标准镜像启用 L2TP/IPSec 支持后重启。",
        ],
    },
    "iphone": {
        "title": "iPhone",
        "steps": [
            "在设置中进入 VPN 与设备管理，添加 VPN 配置。",
            "类型选择 L2TP，填写服务器地址、账号、密码和共享密钥。",
            "开启发送所有流量后保存并连接。",
        ],
    },
    "android": {
        "title": "Android",
        "steps": [
            "Android 12 以下优先使用系统 L2TP/IPSec PSK。",
            "Android 12 及以上使用 UniConnect，协议选择 SSL VPN / OpenConnect 兼容模式。",
            "服务器地址使用 openconnect-ssl 接入点，端口默认 443，用户名和密码使用本系统中的 VPN 账号。",
            "如客户端提示证书不受信任，先从账号连接配置页下载 Wormhole CA 证书并在系统中信任。",
        ],
    },
}


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
        logger.exception("request_failed method=%s path=%s duration_ms=%s", request.method, request.url.path, duration_ms)
        request_id_var.reset(token)
        raise
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    access_logger.info("method=%s path=%s status_code=%s duration_ms=%s", request.method, request.url.path, response.status_code, duration_ms)
    response.headers["x-request-id"] = request_id
    request_id_var.reset(token)
    return response


def sync_radius_rows(
    cursor,
    username: str,
    password: str,
    status: str,
    expiration_at: datetime,
    max_concurrent_sessions: int,
    speed_profile: dict,
) -> None:
    cursor.execute(
        """
        DELETE FROM radcheck
        WHERE username = %s AND attribute IN ('NT-Password', 'Cleartext-Password', 'Expiration', 'Simultaneous-Use')
        """,
        (username,),
    )
    cursor.execute(
        """
        DELETE FROM radreply
        WHERE username = %s
          AND attribute IN ('Filter-Id', 'WISPr-Bandwidth-Max-Up', 'WISPr-Bandwidth-Max-Down')
        """,
        (username,),
    )
    cursor.executemany(
        "INSERT INTO radcheck (username, attribute, op, value) VALUES (%s, %s, ':=', %s)",
        radius_check_rows(username, password, status, expiration_at, max_concurrent_sessions),
    )
    cursor.executemany(
        "INSERT INTO radreply (username, attribute, op, value) VALUES (%s, %s, '=', %s)",
        [
            (username, "Filter-Id", speed_profile["profile_key"]),
            (username, "WISPr-Bandwidth-Max-Up", str(speed_profile["max_up_kbps"] * 1000)),
            (username, "WISPr-Bandwidth-Max-Down", str(speed_profile["max_down_kbps"] * 1000)),
        ],
    )
    try:
        sync_ocserv_user_policy(
            settings.ocserv_config_per_user_dir,
            username,
            speed_profile,
            max_concurrent_sessions,
        )
    except ValueError as exc:
        logger.warning("ocserv_policy_skipped username=%s reason=%s", username, exc)


def bootstrap_admin() -> None:
    with transaction(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM admin_users WHERE username = %s", (settings.admin_username,))
            row = cursor.fetchone()
            password_hash = hash_admin_password(settings.admin_password)
            if row:
                cursor.execute("UPDATE admin_users SET password_hash = %s WHERE id = %s", (password_hash, row["id"]))
            else:
                cursor.execute("INSERT INTO admin_users (username, password_hash) VALUES (%s, %s)", (settings.admin_username, password_hash))


def ensure_speed_profiles() -> None:
    with transaction(settings) as connection:
        with connection.cursor() as cursor:
            for profile_key, display_name, max_up_kbps, max_down_kbps in DEFAULT_SPEED_PROFILES:
                cursor.execute(
                    """
                    INSERT INTO vpn_speed_profiles (profile_key, display_name, max_up_kbps, max_down_kbps)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        display_name = VALUES(display_name),
                        max_up_kbps = VALUES(max_up_kbps),
                        max_down_kbps = VALUES(max_down_kbps)
                    """,
                    (profile_key, display_name, max_up_kbps, max_down_kbps),
                )


def speed_profiles():
    with transaction(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM vpn_speed_profiles ORDER BY max_down_kbps ASC")
            return cursor.fetchall()


def speed_profile_by_id(cursor, speed_profile_id: int) -> dict:
    cursor.execute("SELECT * FROM vpn_speed_profiles WHERE id = %s", (speed_profile_id,))
    profile = cursor.fetchone()
    if not profile:
        raise ValueError(f"speed profile missing: {speed_profile_id}")
    return profile


def default_speed_profile_id(cursor) -> int:
    cursor.execute("SELECT id FROM vpn_speed_profiles WHERE profile_key = %s", (settings.vpn_default_speed_profile,))
    row = cursor.fetchone()
    if row:
        return row["id"]
    cursor.execute("SELECT id FROM vpn_speed_profiles ORDER BY max_down_kbps ASC LIMIT 1")
    fallback = cursor.fetchone()
    if not fallback:
        raise RuntimeError("no speed profiles configured")
    return fallback["id"]


def parse_account_date(date_value: str) -> datetime:
    return to_utc_naive_end_of_day(date_value, settings.timezone_name)


def load_dashboard_accounts():
    refresh_account_events(settings)
    with transaction(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.*,
                    sp.profile_key,
                    sp.display_name AS speed_profile_name,
                    sp.max_up_kbps,
                    sp.max_down_kbps,
                    (
                        SELECT COUNT(*)
                        FROM radacct r
                        WHERE r.username = a.username AND r.acctstoptime IS NULL
                    ) AS active_sessions,
                    (
                        SELECT MAX(authdate)
                        FROM radpostauth p
                        WHERE p.username = a.username AND p.reply = 'Access-Accept'
                    ) AS last_success_at,
                    (
                        SELECT COALESCE(SUM(COALESCE(r.acctinputoctets, 0) + COALESCE(r.acctoutputoctets, 0)), 0)
                        FROM radacct r
                        WHERE r.username = a.username
                    ) AS total_bytes,
                    (
                        SELECT COUNT(*)
                        FROM vpn_account_events e
                        WHERE e.account_id = a.id AND e.status = 'open'
                    ) AS open_events
                FROM vpn_accounts a
                LEFT JOIN vpn_speed_profiles sp ON sp.id = a.speed_profile_id
                ORDER BY a.created_at DESC
                """
            )
            return cursor.fetchall()


def load_account_detail(account_id: int):
    refresh_account_events(settings)
    with transaction(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.*,
                    sp.profile_key,
                    sp.display_name AS speed_profile_name,
                    sp.max_up_kbps,
                    sp.max_down_kbps,
                    (
                        SELECT COUNT(*)
                        FROM radacct r
                        WHERE r.username = a.username AND r.acctstoptime IS NULL
                    ) AS active_sessions,
                    (
                        SELECT MAX(authdate)
                        FROM radpostauth p
                        WHERE p.username = a.username AND p.reply = 'Access-Accept'
                    ) AS last_success_at,
                    (
                        SELECT COALESCE(SUM(COALESCE(r.acctinputoctets, 0) + COALESCE(r.acctoutputoctets, 0)), 0)
                        FROM radacct r
                        WHERE r.username = a.username
                    ) AS total_bytes,
                    (
                        SELECT COALESCE(SUM(COALESCE(r.acctinputoctets, 0) + COALESCE(r.acctoutputoctets, 0)), 0)
                        FROM radacct r
                        WHERE r.username = a.username
                          AND COALESCE(r.acctupdatetime, r.acctstarttime, UTC_TIMESTAMP()) >= UTC_TIMESTAMP() - INTERVAL 5 MINUTE
                    ) AS bytes_5m,
                    (
                        SELECT COALESCE(SUM(COALESCE(r.acctinputoctets, 0) + COALESCE(r.acctoutputoctets, 0)), 0)
                        FROM radacct r
                        WHERE r.username = a.username
                          AND COALESCE(r.acctupdatetime, r.acctstarttime, UTC_TIMESTAMP()) >= UTC_TIMESTAMP() - INTERVAL 1 HOUR
                    ) AS bytes_1h
                FROM vpn_accounts a
                LEFT JOIN vpn_speed_profiles sp ON sp.id = a.speed_profile_id
                WHERE a.id = %s
                """,
                (account_id,),
            )
            account = cursor.fetchone()
            if not account:
                return None

            cursor.execute(
                """
                SELECT
                    acctstarttime,
                    acctupdatetime,
                    framedipaddress,
                    callingstationid,
                    nasipaddress,
                    acctinputoctets,
                    acctoutputoctets
                FROM radacct
                WHERE username = %s AND acctstoptime IS NULL
                ORDER BY acctstarttime DESC
                """,
                (account["username"],),
            )
            active_sessions = cursor.fetchall()

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
                SELECT *
                FROM vpn_account_events
                WHERE account_id = %s
                ORDER BY status = 'open' DESC, detected_at DESC
                LIMIT 20
                """,
                (account_id,),
            )
            events = cursor.fetchall()

            return {
                "account": account,
                "active_sessions": active_sessions,
                "auth_logs": auth_logs,
                "events": events,
                "speed_profiles": speed_profiles(),
                "gateways": settings.vpn_gateways,
                "vpn_shared_psk": settings.vpn_shared_psk,
            }


@app.on_event("startup")
def startup() -> None:
    logger.info("startup_begin")
    wait_for_db(settings)
    ensure_admin_schema(settings)
    bootstrap_admin()
    ensure_speed_profiles()
    refresh_account_events(settings)
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
    return templates.TemplateResponse("login.html", {"request": request, "flash": take_flash(request)})


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
    flash(request, "success", "Logged in.")
    return RedirectResponse(url="/accounts", status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
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
            "speed_profiles": speed_profiles(),
            "flash": take_flash(request),
            "current_admin": current_admin(request),
            "today": datetime.now(LOCAL_ZONE).date().isoformat(),
            "default_max_concurrent_sessions": settings.vpn_max_concurrent_sessions,
        },
    )


@app.post("/accounts")
def create_account(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    expiration_date: str = Form(...),
    speed_profile_id: int = Form(...),
    max_concurrent_sessions: int = Form(...),
):
    redirect = require_login(request)
    if redirect:
        return redirect
    try:
        validate_ocserv_username(username)
    except ValueError as exc:
        flash(request, "error", f"Invalid username: {exc}")
        return RedirectResponse(url="/accounts", status_code=303)
    expiration_at = parse_account_date(expiration_date)
    try:
        with transaction(settings) as connection:
            with connection.cursor() as cursor:
                if speed_profile_id <= 0:
                    speed_profile_id = default_speed_profile_id(cursor)
                speed_profile = speed_profile_by_id(cursor, speed_profile_id)
                cursor.execute(
                    """
                    INSERT INTO vpn_accounts
                        (username, password_plaintext, status, expiration_at, speed_profile_id, max_concurrent_sessions)
                    VALUES (%s, %s, 'enabled', %s, %s, %s)
                    """,
                    (username, password, expiration_at, speed_profile_id, max_concurrent_sessions),
                )
                sync_radius_rows(cursor, username, password, "enabled", expiration_at, max_concurrent_sessions, speed_profile)
    except Exception:
        logger.exception("account_create_failed username=%s", username)
        flash(request, "error", f"Failed to create account: {username}")
        return RedirectResponse(url="/accounts", status_code=303)
    flash(request, "success", f"Account {username} created.")
    return RedirectResponse(url="/accounts", status_code=303)


@app.get("/accounts/{account_id}", response_class=HTMLResponse)
def account_detail(request: Request, account_id: int):
    redirect = require_login(request)
    if redirect:
        return redirect
    payload = load_account_detail(account_id)
    if payload is None:
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
                speed_profile = speed_profile_by_id(cursor, account["speed_profile_id"])
                cursor.execute("UPDATE vpn_accounts SET expiration_at = %s WHERE id = %s", (expiration_at, account_id))
                sync_radius_rows(
                    cursor,
                    account["username"],
                    account["password_plaintext"],
                    account["status"],
                    expiration_at,
                    account["max_concurrent_sessions"],
                    speed_profile,
                )
    except Exception:
        logger.exception("account_extend_failed account_id=%s", account_id)
        flash(request, "error", "Failed to update expiration.")
        return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)
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
                speed_profile = speed_profile_by_id(cursor, account["speed_profile_id"])
                new_status = "disabled" if account["status"] == "enabled" else "enabled"
                cursor.execute("UPDATE vpn_accounts SET status = %s WHERE id = %s", (new_status, account_id))
                sync_radius_rows(
                    cursor,
                    account["username"],
                    account["password_plaintext"],
                    new_status,
                    account["expiration_at"],
                    account["max_concurrent_sessions"],
                    speed_profile,
                )
    except Exception:
        logger.exception("account_toggle_failed account_id=%s", account_id)
        flash(request, "error", "Failed to update account status.")
        return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)
    flash(request, "success", f"Account {new_status}.")
    return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)


@app.post("/accounts/{account_id}/password")
def rotate_password(request: Request, account_id: int, password: str = Form(...)):
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
                speed_profile = speed_profile_by_id(cursor, account["speed_profile_id"])
                cursor.execute("UPDATE vpn_accounts SET password_plaintext = %s WHERE id = %s", (password, account_id))
                sync_radius_rows(
                    cursor,
                    account["username"],
                    password,
                    account["status"],
                    account["expiration_at"],
                    account["max_concurrent_sessions"],
                    speed_profile,
                )
    except Exception:
        logger.exception("account_password_rotate_failed account_id=%s", account_id)
        flash(request, "error", "Failed to rotate VPN password.")
        return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)
    flash(request, "success", "VPN password updated.")
    return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)


@app.post("/accounts/{account_id}/settings")
def update_account_settings(
    request: Request,
    account_id: int,
    speed_profile_id: int = Form(...),
    max_concurrent_sessions: int = Form(...),
):
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
                speed_profile = speed_profile_by_id(cursor, speed_profile_id)
                cursor.execute(
                    """
                    UPDATE vpn_accounts
                    SET speed_profile_id = %s, max_concurrent_sessions = %s
                    WHERE id = %s
                    """,
                    (speed_profile_id, max_concurrent_sessions, account_id),
                )
                sync_radius_rows(
                    cursor,
                    account["username"],
                    account["password_plaintext"],
                    account["status"],
                    account["expiration_at"],
                    max_concurrent_sessions,
                    speed_profile,
                )
    except Exception:
        logger.exception("account_settings_update_failed account_id=%s", account_id)
        flash(request, "error", "Failed to update account policy.")
        return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)
    flash(request, "success", "Account policy updated.")
    return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)


@app.post("/events/{event_id}/resolve")
def resolve_event(request: Request, event_id: int):
    redirect = require_login(request)
    if redirect:
        return redirect
    with transaction(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT account_id FROM vpn_account_events WHERE id = %s", (event_id,))
            event = cursor.fetchone()
            if not event:
                flash(request, "error", "Event not found.")
                return RedirectResponse(url="/accounts", status_code=303)
            cursor.execute(
                """
                UPDATE vpn_account_events
                SET status = 'resolved', resolved_at = UTC_TIMESTAMP()
                WHERE id = %s
                """,
                (event_id,),
            )
    flash(request, "success", "Event resolved.")
    return RedirectResponse(url=f"/accounts/{event['account_id']}", status_code=303)


@app.post("/events/{event_id}/disable-account")
def disable_account_from_event(request: Request, event_id: int):
    redirect = require_login(request)
    if redirect:
        return redirect
    with transaction(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT e.account_id, a.*
                FROM vpn_account_events e
                JOIN vpn_accounts a ON a.id = e.account_id
                WHERE e.id = %s
                """,
                (event_id,),
            )
            payload = cursor.fetchone()
            if not payload:
                flash(request, "error", "Event not found.")
                return RedirectResponse(url="/accounts", status_code=303)
            speed_profile = speed_profile_by_id(cursor, payload["speed_profile_id"])
            cursor.execute("UPDATE vpn_accounts SET status = 'disabled' WHERE id = %s", (payload["account_id"],))
            cursor.execute(
                """
                UPDATE vpn_account_events
                SET status = 'resolved', resolved_at = UTC_TIMESTAMP()
                WHERE id = %s
                """,
                (event_id,),
            )
            sync_radius_rows(
                cursor,
                payload["username"],
                payload["password_plaintext"],
                "disabled",
                payload["expiration_at"],
                payload["max_concurrent_sessions"],
                speed_profile,
            )
    flash(request, "success", "Account disabled.")
    return RedirectResponse(url=f"/accounts/{payload['account_id']}", status_code=303)


@app.get("/accounts/{account_id}/connection-config")
def connection_config(request: Request, account_id: int):
    redirect = require_login(request)
    if redirect:
        return redirect
    with transaction(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.username, a.status, a.max_concurrent_sessions, sp.profile_key, sp.display_name
                FROM vpn_accounts a
                LEFT JOIN vpn_speed_profiles sp ON sp.id = a.speed_profile_id
                WHERE a.id = %s
                """,
                (account_id,),
            )
            account = cursor.fetchone()
    if not account:
        return JSONResponse(status_code=404, content={"detail": "account not found"})
    return build_connection_config(
        account=account,
        gateways=settings.vpn_gateways,
        vpn_shared_psk=settings.vpn_shared_psk,
        ca_certificate_url=str(request.url_for("download_ca_certificate")),
    )


@app.get("/accounts/{account_id}/macos-installer")
def download_macos_installer(request: Request, account_id: int):
    redirect = require_login(request)
    if redirect:
        return redirect
    with transaction(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT username, password_plaintext
                FROM vpn_accounts
                WHERE id = %s
                """,
                (account_id,),
            )
            account = cursor.fetchone()
    if not account:
        return JSONResponse(status_code=404, content={"detail": "account not found"})
    try:
        filename, payload = build_macos_installer_archive(
            username=account["username"],
            password=account["password_plaintext"],
            vpn_shared_psk=settings.vpn_shared_psk,
            gateways=settings.vpn_gateways,
        )
    except ValueError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    logger.info("macos_installer_downloaded account_id=%s username=%s", account_id, account["username"])
    return Response(
        content=payload,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/ca-certificates/root")
def download_ca_certificate(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    try:
        payload = CAClient(settings).download_ca_certificate()
    except Exception:
        logger.exception("ca_certificate_proxy_failed")
        return JSONResponse(status_code=502, content={"detail": "failed to fetch CA certificate"})
    headers = {"Content-Disposition": 'attachment; filename="wormhole-ca-cert.pem"'}
    return Response(content=payload, media_type="application/x-pem-file", headers=headers)


@app.get("/guides/{platform}", response_class=HTMLResponse)
def platform_guide(request: Request, platform: str):
    redirect = require_login(request)
    if redirect:
        return redirect
    guide = PLATFORM_GUIDES.get(platform)
    if guide is None:
        return HTMLResponse("guide not found", status_code=404)
    return templates.TemplateResponse(
        "platform_guide.html",
        {"request": request, "guide": guide, "flash": take_flash(request), "current_admin": current_admin(request)},
    )
