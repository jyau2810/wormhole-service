from __future__ import annotations

import logging

from .db import transaction
from .settings import Settings

logger = logging.getLogger("wormhole.app")


def _has_table(cursor, table_name: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        LIMIT 1
        """,
        (table_name,),
    )
    return cursor.fetchone() is not None


def _has_column(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
        LIMIT 1
        """,
        (table_name, column_name),
    )
    return cursor.fetchone() is not None


def _has_constraint(cursor, table_name: str, constraint_name: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.TABLE_CONSTRAINTS
        WHERE CONSTRAINT_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND CONSTRAINT_NAME = %s
        LIMIT 1
        """,
        (table_name, constraint_name),
    )
    return cursor.fetchone() is not None


def ensure_admin_schema(settings: Settings) -> None:
    with transaction(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS vpn_speed_profiles (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    profile_key VARCHAR(64) NOT NULL,
                    display_name VARCHAR(128) NOT NULL,
                    max_up_kbps INT UNSIGNED NOT NULL,
                    max_down_kbps INT UNSIGNED NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY uq_vpn_speed_profiles_key (profile_key)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )

            if not _has_table(cursor, "vpn_accounts"):
                cursor.execute(
                    """
                    CREATE TABLE vpn_accounts (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        username VARCHAR(64) NOT NULL,
                        password_plaintext VARCHAR(255) NOT NULL,
                        status ENUM('enabled', 'disabled') NOT NULL DEFAULT 'enabled',
                        expiration_at DATETIME NOT NULL,
                        speed_profile_id BIGINT UNSIGNED DEFAULT NULL,
                        max_concurrent_sessions TINYINT UNSIGNED NOT NULL DEFAULT 1,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (id),
                        UNIQUE KEY uq_vpn_accounts_username (username)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )

            if not _has_column(cursor, "vpn_accounts", "speed_profile_id"):
                cursor.execute("ALTER TABLE vpn_accounts ADD COLUMN speed_profile_id BIGINT UNSIGNED DEFAULT NULL AFTER expiration_at")
                logger.info("schema_updated table=vpn_accounts column=speed_profile_id")

            if not _has_column(cursor, "vpn_accounts", "max_concurrent_sessions"):
                cursor.execute(
                    """
                    ALTER TABLE vpn_accounts
                    ADD COLUMN max_concurrent_sessions TINYINT UNSIGNED NOT NULL DEFAULT 1
                    AFTER speed_profile_id
                    """
                )
                logger.info("schema_updated table=vpn_accounts column=max_concurrent_sessions")

            if (
                _has_column(cursor, "vpn_accounts", "speed_profile_id")
                and _has_table(cursor, "vpn_speed_profiles")
                and not _has_constraint(cursor, "vpn_accounts", "fk_vpn_accounts_speed_profile")
            ):
                cursor.execute(
                    """
                    ALTER TABLE vpn_accounts
                    ADD CONSTRAINT fk_vpn_accounts_speed_profile
                    FOREIGN KEY (speed_profile_id) REFERENCES vpn_speed_profiles(id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE
                    """
                )
                logger.info("schema_updated table=vpn_accounts constraint=fk_vpn_accounts_speed_profile")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS vpn_account_events (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    account_id BIGINT UNSIGNED NOT NULL,
                    event_type VARCHAR(64) NOT NULL,
                    severity ENUM('info', 'warning', 'critical') NOT NULL DEFAULT 'warning',
                    status ENUM('open', 'resolved') NOT NULL DEFAULT 'open',
                    details_json JSON NOT NULL,
                    detected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    resolved_at DATETIME DEFAULT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    KEY idx_vpn_account_events_account_status (account_id, status),
                    KEY idx_vpn_account_events_type_status (event_type, status),
                    CONSTRAINT fk_vpn_account_events_account
                        FOREIGN KEY (account_id) REFERENCES vpn_accounts(id)
                        ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
