# 环境变量

英文原版请见 [env.md](/Users/yaoji/Documents/Workspace/wormhole-service/env.md)。

## 数据库

| 变量 | 必填 | 默认值 | 用途 |
| --- | --- | --- | --- |
| `MARIADB_DATABASE` | 是 | `radius` | 首次启动时创建的 MariaDB 数据库。 |
| `MARIADB_USER` | 是 | `radius` | 应用数据库用户。 |
| `MARIADB_PASSWORD` | 是 | 无 | 应用数据库用户密码。 |
| `MARIADB_ROOT_PASSWORD` | 是 | 无 | MariaDB root 密码，用于初始化和恢复。 |
| `MYSQL_GENERAL_LOG` | 是 | `OFF` | 是否开启 MariaDB general query log；除排障外建议关闭。 |
| `MYSQL_SLOW_LOG_THRESHOLD_MS` | 是 | `1000` | MariaDB 慢查询阈值，单位毫秒。 |
| `RADIUS_DB_PORT` | 是 | `3306` | FreeRADIUS 和后台使用的内部 MariaDB 端口。 |
| `RADIUS_DB_NAME` | 是 | `radius` | 内部服务使用的数据库名。 |
| `RADIUS_DB_USER` | 是 | `radius` | FreeRADIUS 和后台使用的数据库账号。 |
| `RADIUS_DB_PASSWORD` | 是 | 无 | FreeRADIUS 和后台使用的数据库密码。 |

## 后台与内部 API

| 变量 | 必填 | 默认值 | 用途 |
| --- | --- | --- | --- |
| `APP_TIMEZONE` | 是 | `Asia/Shanghai` | 后台与 CA API 的展示和日期解析时区。 |
| `LOG_LEVEL` | 是 | `INFO` | Python 服务业务日志与访问日志级别。 |
| `LOG_DIR_ROOT` | 是 | `/var/log/wormhole` | 所有容器内日志文件使用的根目录。 |
| `LOG_RETENTION_DAYS` | 是 | `7` | `logrotate` sidecar 保留滚动日志的天数。 |
| `ADMIN_PORTAL_PORT` | 是 | `8080` | 宿主机映射给管理后台的端口，默认仅绑定回环地址。 |
| `ADMIN_BIND_PORT` | 是 | `8000` | 管理后台容器内部监听端口。 |
| `ADMIN_USERNAME` | 是 | `admin` | 初始化管理员用户名。 |
| `ADMIN_PASSWORD` | 是 | 无 | 初始化管理员密码。 |
| `ADMIN_SESSION_SECRET` | 是 | 无 | 会话 Cookie 密钥，必须足够长且随机。 |
| `CA_API_TOKEN` | 是 | 无 | 管理后台访问 CA API 时使用的 Bearer Token。 |
| `INTERNAL_API_BIND_PORT` | 是 | `9000` | CA API 容器内部监听端口。 |

## 证书机构

| 变量 | 必填 | 默认值 | 用途 |
| --- | --- | --- | --- |
| `CA_COMMON_NAME` | 是 | `Wormhole VPN Internal CA` | 内部 CA 证书通用名。 |
| `CA_ORGANIZATION` | 是 | `Wormhole VPN` | 内部 CA 组织名。 |
| `CA_VALIDITY_DAYS` | 是 | `3650` | 根 CA 证书有效期，单位天。 |
| `SERVER_CERT_VALIDITY_DAYS` | 是 | `825` | VPN 服务端证书有效期，单位天。 |
| `CLIENT_CERT_VALIDITY_DAYS` | 是 | `365` | 客户端证书有效期，单位天。 |
| `P12_EXPORT_PASSWORD` | 否 | 空 | 导出的客户端 PKCS#12 文件可选保护密码。 |

## VPN

| 变量 | 必填 | 默认值 | 用途 |
| --- | --- | --- | --- |
| `VPN_SERVER_HOST` | 是 | 无 | 客户端连接使用的公网域名或 IP，也用于生成服务端证书 SAN。 |
| `VPN_SERVER_ALT_NAMES` | 否 | 空 | VPN 服务端证书额外 SAN，逗号分隔。 |
| `VPN_TCP_PORT` | 是 | `443` | ocserv 暴露的 TCP 端口。 |
| `VPN_UDP_PORT` | 是 | `443` | ocserv 暴露的 UDP 端口。 |
| `VPN_NETWORK` | 是 | `10.88.0.0` | 分配给 VPN 客户端的隧道网段。 |
| `VPN_NETMASK` | 是 | `255.255.255.0` | 隧道子网掩码。 |
| `VPN_MAX_CLIENTS` | 是 | `16` | ocserv 最大并发客户端数。 |
| `VPN_DNS_1` | 是 | `1.1.1.1` | 下发给客户端的主 DNS。 |
| `VPN_DNS_2` | 是 | `8.8.8.8` | 下发给客户端的备用 DNS。 |
| `VPN_IDLE_TIMEOUT` | 是 | `1200` | 桌面端空闲超时，单位秒。 |
| `VPN_MOBILE_IDLE_TIMEOUT` | 是 | `1800` | 移动端空闲超时，单位秒。 |
| `VPN_SESSION_TIMEOUT` | 是 | `28800` | 单次登录最大会话时长，单位秒。 |
| `VPN_STATS_REPORT_TIME` | 是 | `300` | ocserv 会话统计上报周期，单位秒。 |
| `VPN_DEFAULT_DOMAIN` | 否 | 空 | 可选的客户端搜索域。 |
| `OCSERV_NAT_DEVICE` | 是 | `eth0` | ocserv 容器内用于 NAT masquerade 的出口网卡。 |
| `RADIUS_SHARED_SECRET` | 是 | 无 | ocserv 与 FreeRADIUS 之间的共享密钥。 |
