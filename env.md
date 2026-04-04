# Environment Variables

## Database

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `MARIADB_DATABASE` | Yes | `radius` | MariaDB database created on first boot. |
| `MARIADB_USER` | Yes | `radius` | Application database user. |
| `MARIADB_PASSWORD` | Yes | None | Password for the application database user. |
| `MARIADB_ROOT_PASSWORD` | Yes | None | MariaDB root password for bootstrap and recovery. |
| `MYSQL_GENERAL_LOG` | Yes | `OFF` | MariaDB general query logging. |
| `MYSQL_SLOW_LOG_THRESHOLD_MS` | Yes | `1000` | Slow query threshold in milliseconds. |
| `RADIUS_DB_PORT` | Yes | `3306` | Internal MariaDB port used by FreeRADIUS and the portal. |
| `RADIUS_DB_NAME` | Yes | `radius` | Database name used by internal services. |
| `RADIUS_DB_USER` | Yes | `radius` | Database login used by FreeRADIUS and the portal. |
| `RADIUS_DB_PASSWORD` | Yes | None | Database password used by FreeRADIUS and the portal. |

## Portal

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `APP_TIMEZONE` | Yes | `Asia/Shanghai` | Display and date parsing timezone for the portal. |
| `LOG_LEVEL` | Yes | `INFO` | Portal and service log level. |
| `LOG_DIR_ROOT` | Yes | `/var/log/wormhole` | In-container root directory for service logs. |
| `LOG_RETENTION_DAYS` | Yes | `7` | Number of days rotated logs are kept. |
| `ADMIN_PORTAL_PORT` | Yes | `8080` | Host port bound to the admin portal, loopback only by default. |
| `ADMIN_BIND_PORT` | Yes | `8000` | Internal container port for the admin portal. |
| `ADMIN_USERNAME` | Yes | `admin` | Bootstrap administrator username. |
| `ADMIN_PASSWORD` | Yes | None | Bootstrap administrator password. |
| `ADMIN_SESSION_SECRET` | Yes | None | Session cookie secret; keep it long and random. |
| `VPN_SHARED_PSK` | Yes | None | IPSec pre-shared key displayed in the portal and used by strongSwan. |
| `VPN_DEFAULT_SPEED_PROFILE` | Yes | `standard-10m` | Default profile key assigned to newly created VPN accounts. |
| `VPN_MAX_CONCURRENT_SESSIONS` | Yes | `1` | Default per-account concurrent-session limit. |
| `VPN_GATEWAYS` | Yes | JSON array | Public gateway metadata shown in the portal and exported by the config endpoint. |

## VPN Gateway

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `VPN_IPSEC_IKE_PORT` | Yes | `500` | UDP IKE port exposed by strongSwan. |
| `VPN_IPSEC_NATT_PORT` | Yes | `4500` | UDP NAT-T port exposed by strongSwan. |
| `VPN_L2TP_PORT` | Yes | `1701` | UDP L2TP port exposed by accel-ppp. |
| `VPN_RADIUS_AUTH_PORT` | Yes | `1812` | RADIUS auth port used by accel-ppp. |
| `VPN_RADIUS_ACCT_PORT` | Yes | `1813` | RADIUS accounting port used by accel-ppp. |
| `VPN_NAS_IDENTIFIER` | Yes | `wormhole-l2tp` | NAS identifier sent to FreeRADIUS. |
| `VPN_NAS_IP_ADDRESS` | Yes | `127.0.0.1` | NAS IP address sent to FreeRADIUS records. |
| `VPN_NETWORK` | Yes | `10.88.0.0` | Client pool network. |
| `VPN_NETMASK` | Yes | `255.255.255.0` | Client pool netmask. |
| `VPN_GATEWAY_IP` | Yes | `10.88.0.1` | Gateway IP handed to PPP clients. |
| `VPN_DNS_1` | Yes | `1.1.1.1` | Primary DNS server pushed to clients. |
| `VPN_DNS_2` | Yes | `8.8.8.8` | Secondary DNS server pushed to clients. |
| `VPN_MTU` | Yes | `1400` | PPP MTU/MRU used by accel-ppp. |
| `VPN_NAT_DEVICE` | Yes | `eth0` | Outbound interface used for NAT masquerading inside the gateway container. |
| `RADIUS_SHARED_SECRET` | Yes | None | Shared secret between accel-ppp and FreeRADIUS. |
