# Environment Variables

## Database

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `MARIADB_DATABASE` | Yes | `radius` | MariaDB database created on first boot. |
| `MARIADB_USER` | Yes | `radius` | Application database user. |
| `MARIADB_PASSWORD` | Yes | None | Password for the application database user. |
| `MARIADB_ROOT_PASSWORD` | Yes | None | MariaDB root password for bootstrap and recovery. |
| `MYSQL_GENERAL_LOG` | Yes | `OFF` | Whether MariaDB general query logging is enabled; keep it off unless debugging. |
| `MYSQL_SLOW_LOG_THRESHOLD_MS` | Yes | `1000` | Slow query threshold written into the MariaDB log config, in milliseconds. |
| `RADIUS_DB_PORT` | Yes | `3306` | Internal MariaDB port used by FreeRADIUS and the portal. |
| `RADIUS_DB_NAME` | Yes | `radius` | Database name used by all internal services. |
| `RADIUS_DB_USER` | Yes | `radius` | Database login used by FreeRADIUS and the portal. |
| `RADIUS_DB_PASSWORD` | Yes | None | Database password used by FreeRADIUS and the portal. |

## Portal and Internal API

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `APP_TIMEZONE` | Yes | `Asia/Shanghai` | Display and date parsing timezone for the portal and CA API. |
| `LOG_LEVEL` | Yes | `INFO` | Python service log level for application and access logs. |
| `LOG_DIR_ROOT` | Yes | `/var/log/wormhole` | In-container root directory used by all service log files. |
| `LOG_RETENTION_DAYS` | Yes | `7` | Number of days the logrotate sidecar keeps rotated logs. |
| `ADMIN_PORTAL_PORT` | Yes | `8080` | Host port bound to the admin portal, loopback only by default. |
| `ADMIN_BIND_PORT` | Yes | `8000` | Internal container port used by the admin portal. |
| `ADMIN_USERNAME` | Yes | `admin` | Bootstrap administrator username. |
| `ADMIN_PASSWORD` | Yes | None | Bootstrap administrator password. |
| `ADMIN_SESSION_SECRET` | Yes | None | Session cookie secret; keep it long and random. |
| `CA_API_TOKEN` | Yes | None | Shared bearer token used by the admin portal to call the CA API. |
| `INTERNAL_API_BIND_PORT` | Yes | `9000` | Internal CA API bind port. |

## Certificate Authority

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `CA_COMMON_NAME` | Yes | `Wormhole VPN Internal CA` | Internal CA certificate common name. |
| `CA_ORGANIZATION` | Yes | `Wormhole VPN` | Internal CA organization string. |
| `CA_VALIDITY_DAYS` | Yes | `3650` | Root CA validity period in days. |
| `SERVER_CERT_VALIDITY_DAYS` | Yes | `825` | VPN server certificate validity period in days. |
| `CLIENT_CERT_VALIDITY_DAYS` | Yes | `365` | Client certificate validity period in days. |
| `P12_EXPORT_PASSWORD` | No | empty | Optional password applied to exported client PKCS#12 bundles. |

## VPN

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `VPN_SERVER_HOST` | Yes | None | Public hostname or IP clients connect to; used in generated server cert SANs. |
| `VPN_SERVER_ALT_NAMES` | No | empty | Comma-separated extra SAN entries for the VPN server certificate. |
| `VPN_TCP_PORT` | Yes | `443` | TCP port exposed by ocserv. |
| `VPN_UDP_PORT` | Yes | `443` | UDP port exposed by ocserv. |
| `VPN_NETWORK` | Yes | `10.88.0.0` | Tunnel subnet assigned to VPN clients. |
| `VPN_NETMASK` | Yes | `255.255.255.0` | Tunnel netmask. |
| `VPN_MAX_CLIENTS` | Yes | `16` | ocserv maximum concurrent clients. |
| `VPN_DNS_1` | Yes | `1.1.1.1` | Primary DNS server pushed to clients. |
| `VPN_DNS_2` | Yes | `8.8.8.8` | Secondary DNS server pushed to clients. |
| `VPN_IDLE_TIMEOUT` | Yes | `1200` | Idle timeout for desktop-class sessions, in seconds. |
| `VPN_MOBILE_IDLE_TIMEOUT` | Yes | `1800` | Idle timeout for mobile sessions, in seconds. |
| `VPN_SESSION_TIMEOUT` | Yes | `28800` | Maximum session time per login, in seconds. |
| `VPN_STATS_REPORT_TIME` | Yes | `300` | ocserv session statistics reporting interval, in seconds. |
| `VPN_DEFAULT_DOMAIN` | No | empty | Optional search domain pushed to clients. |
| `OCSERV_NAT_DEVICE` | Yes | `eth0` | Outbound interface used for NAT masquerading inside the ocserv container. |
| `RADIUS_SHARED_SECRET` | Yes | None | Shared secret between ocserv and FreeRADIUS. |
