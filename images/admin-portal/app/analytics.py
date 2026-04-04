from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from decimal import Decimal

from .db import transaction
from .settings import Settings

logger = logging.getLogger("wormhole.app")


@dataclass(frozen=True)
class AccountSignal:
    account_id: int
    active_sessions: int
    max_concurrent_sessions: int
    recent_rejects: int
    recent_gateway_count: int
    bytes_5m: int
    profile_limit_kbps: int


def _expected_bytes_for_5m(limit_kbps: int) -> int:
    normalized_limit_kbps = int(limit_kbps)
    return normalized_limit_kbps * 1000 * 300 * 12 // 80


def _normalize_account_signal(row: dict) -> AccountSignal:
    normalized = {
        key: int(value) if isinstance(value, Decimal) else value
        for key, value in row.items()
    }
    return AccountSignal(**normalized)


def refresh_account_events(settings: Settings) -> None:
    with transaction(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.id AS account_id,
                    a.max_concurrent_sessions,
                    COALESCE(sp.max_up_kbps, 0) + COALESCE(sp.max_down_kbps, 0) AS profile_limit_kbps,
                    (
                        SELECT COUNT(*)
                        FROM radacct r
                        WHERE r.username = a.username AND r.acctstoptime IS NULL
                    ) AS active_sessions,
                    (
                        SELECT COUNT(*)
                        FROM radpostauth p
                        WHERE p.username = a.username
                          AND p.reply = 'Access-Reject'
                          AND p.authdate >= UTC_TIMESTAMP() - INTERVAL 15 MINUTE
                    ) AS recent_rejects,
                    (
                        SELECT COUNT(DISTINCT r.nasipaddress)
                        FROM radacct r
                        WHERE r.username = a.username
                          AND r.acctstarttime >= UTC_TIMESTAMP() - INTERVAL 30 MINUTE
                    ) AS recent_gateway_count,
                    (
                        SELECT COALESCE(SUM(COALESCE(r.acctinputoctets, 0) + COALESCE(r.acctoutputoctets, 0)), 0)
                        FROM radacct r
                        WHERE r.username = a.username
                          AND COALESCE(r.acctupdatetime, r.acctstarttime, UTC_TIMESTAMP()) >= UTC_TIMESTAMP() - INTERVAL 5 MINUTE
                    ) AS bytes_5m
                FROM vpn_accounts a
                LEFT JOIN vpn_speed_profiles sp ON sp.id = a.speed_profile_id
                """
            )
            rows = [_normalize_account_signal(row) for row in cursor.fetchall()]

            active_by_account: dict[int, set[str]] = {}
            for row in rows:
                issues: dict[str, dict[str, int]] = {}
                if row.active_sessions > row.max_concurrent_sessions:
                    issues["concurrent_sessions_exceeded"] = {
                        "active_sessions": row.active_sessions,
                        "max_concurrent_sessions": row.max_concurrent_sessions,
                    }
                if row.recent_rejects >= 5:
                    issues["repeated_auth_rejects"] = {"recent_rejects": row.recent_rejects}
                if row.recent_gateway_count >= 3:
                    issues["gateway_hop_detected"] = {"recent_gateway_count": row.recent_gateway_count}
                if row.profile_limit_kbps > 0 and row.bytes_5m > _expected_bytes_for_5m(row.profile_limit_kbps):
                    issues["traffic_spike_detected"] = {
                        "bytes_5m": row.bytes_5m,
                        "threshold_5m": _expected_bytes_for_5m(row.profile_limit_kbps),
                    }

                active_by_account[row.account_id] = set(issues)
                for event_type, payload in issues.items():
                    cursor.execute(
                        """
                        SELECT id
                        FROM vpn_account_events
                        WHERE account_id = %s AND event_type = %s AND status = 'open'
                        """,
                        (row.account_id, event_type),
                    )
                    existing = cursor.fetchone()
                    details = json.dumps(payload, ensure_ascii=True, sort_keys=True)
                    if existing:
                        cursor.execute(
                            """
                            UPDATE vpn_account_events
                            SET details_json = %s, detected_at = UTC_TIMESTAMP()
                            WHERE id = %s
                            """,
                            (details, existing["id"]),
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO vpn_account_events
                                (account_id, event_type, severity, status, details_json, detected_at)
                            VALUES (%s, %s, 'warning', 'open', %s, UTC_TIMESTAMP())
                            """,
                            (row.account_id, event_type, details),
                        )

            cursor.execute(
                """
                SELECT id, account_id, event_type
                FROM vpn_account_events
                WHERE status = 'open'
                """
            )
            for row in cursor.fetchall():
                if row["event_type"] not in active_by_account.get(row["account_id"], set()):
                    cursor.execute(
                        """
                        UPDATE vpn_account_events
                        SET status = 'resolved', resolved_at = UTC_TIMESTAMP()
                        WHERE id = %s
                        """,
                        (row["id"],),
                    )

    logger.info("account_events_refreshed count=%s", len(rows))
