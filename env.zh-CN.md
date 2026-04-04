# 环境变量

英文原版请见 [env.md](/Users/jyau/Documents/Projects/wormhole-service/env.md)。

## 数据库

| 变量 | 必填 | 默认值 | 用途 |
| --- | --- | --- | --- |
| `MARIADB_DATABASE` | 是 | `radius` | 首次启动时创建的 MariaDB 数据库。 |
| `MARIADB_USER` | 是 | `radius` | 应用数据库用户。 |
| `MARIADB_PASSWORD` | 是 | 无 | 应用数据库用户密码。 |
| `MARIADB_ROOT_PASSWORD` | 是 | 无 | MariaDB root 密码。 |
| `MYSQL_GENERAL_LOG` | 是 | `OFF` | 是否开启 MariaDB general log。 |
| `MYSQL_SLOW_LOG_THRESHOLD_MS` | 是 | `1000` | 慢查询阈值，单位毫秒。 |
| `RADIUS_DB_PORT` | 是 | `3306` | FreeRADIUS 和后台使用的内部 MariaDB 端口。 |
| `RADIUS_DB_NAME` | 是 | `radius` | 内部服务使用的数据库名。 |
| `RADIUS_DB_USER` | 是 | `radius` | FreeRADIUS 和后台使用的数据库账号。 |
| `RADIUS_DB_PASSWORD` | 是 | 无 | FreeRADIUS 和后台使用的数据库密码。 |

## 后台

| 变量 | 必填 | 默认值 | 用途 |
| --- | --- | --- | --- |
| `APP_TIMEZONE` | 是 | `Asia/Shanghai` | 后台展示和日期解析时区。 |
| `LOG_LEVEL` | 是 | `INFO` | 服务日志级别。 |
| `LOG_DIR_ROOT` | 是 | `/var/log/wormhole` | 容器内日志根目录。 |
| `LOG_RETENTION_DAYS` | 是 | `7` | 日志保留天数。 |
| `ADMIN_PORTAL_PORT` | 是 | `8080` | 宿主机映射给后台的端口。 |
| `ADMIN_BIND_PORT` | 是 | `8000` | 后台容器内部监听端口。 |
| `ADMIN_USERNAME` | 是 | `admin` | 初始化管理员用户名。 |
| `ADMIN_PASSWORD` | 是 | 无 | 初始化管理员密码。 |
| `ADMIN_SESSION_SECRET` | 是 | 无 | 会话 Cookie 密钥。 |
| `VPN_SHARED_PSK` | 是 | 无 | L2TP/IPSec 使用的共享密钥，同时在后台展示。 |
| `VPN_DEFAULT_SPEED_PROFILE` | 是 | `standard-10m` | 新账号默认限速档位。 |
| `VPN_MAX_CONCURRENT_SESSIONS` | 是 | `1` | 新账号默认最大并发会话数。 |
| `VPN_GATEWAYS` | 是 | JSON 数组 | 后台展示和配置导出的接入点列表。 |

## VPN 网关

| 变量 | 必填 | 默认值 | 用途 |
| --- | --- | --- | --- |
| `VPN_IPSEC_IKE_PORT` | 是 | `500` | strongSwan 暴露的 IKE UDP 端口。 |
| `VPN_IPSEC_NATT_PORT` | 是 | `4500` | strongSwan 暴露的 NAT-T UDP 端口。 |
| `VPN_L2TP_PORT` | 是 | `1701` | accel-ppp 暴露的 L2TP UDP 端口。 |
| `VPN_RADIUS_AUTH_PORT` | 是 | `1812` | accel-ppp 使用的 RADIUS 鉴权端口。 |
| `VPN_RADIUS_ACCT_PORT` | 是 | `1813` | accel-ppp 使用的 RADIUS 记账端口。 |
| `VPN_NAS_IDENTIFIER` | 是 | `wormhole-l2tp` | 写入 RADIUS 的 NAS 标识。 |
| `VPN_NAS_IP_ADDRESS` | 是 | `127.0.0.1` | 写入 RADIUS 记录的 NAS IP。 |
| `VPN_NETWORK` | 是 | `10.88.0.0` | VPN 客户端地址池网段。 |
| `VPN_NETMASK` | 是 | `255.255.255.0` | VPN 客户端地址池掩码。 |
| `VPN_GATEWAY_IP` | 是 | `10.88.0.1` | PPP 网关地址。 |
| `VPN_DNS_1` | 是 | `1.1.1.1` | 下发给客户端的主 DNS。 |
| `VPN_DNS_2` | 是 | `8.8.8.8` | 下发给客户端的备用 DNS。 |
| `VPN_MTU` | 是 | `1400` | PPP MTU/MRU。 |
| `VPN_NAT_DEVICE` | 是 | `eth0` | 网关容器内用于 NAT 的出口网卡。 |
| `RADIUS_SHARED_SECRET` | 是 | 无 | accel-ppp 与 FreeRADIUS 的共享密钥。 |
