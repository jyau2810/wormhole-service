# 环境变量说明

本文档解释 `.env.example` 中出现的全部环境变量。配置面已经做过代码层精简，但文档仍然覆盖每一个实际变量，方便部署、排障和逐项核对。

## 使用方式

```bash
cp .env.example .env
```

首次部署至少修改这些项：

- `DB_PASSWORD`
- `MARIADB_ROOT_PASSWORD`
- `RADIUS_SHARED_SECRET`
- `ADMIN_PASSWORD`
- `ADMIN_SESSION_SECRET`
- `VPN_SHARED_PSK`
- `VPN_GATEWAYS`
- `VPN_NAT_DEVICE`

## 通用与日志

### `APP_TIMEZONE`

- 默认值：`Asia/Shanghai`
- 用途：影响后台展示时间、日志时间解析以及账号到期时间的解释方式。
- 建议：一般保持默认。

### `LOG_LEVEL`

- 默认值：`INFO`
- 用途：控制后台应用日志级别。
- 常见取值：`DEBUG`、`INFO`、`WARNING`、`ERROR`
- 建议：排障时再临时调高详细度。

### `LOG_DIR_ROOT`

- 默认值：`/var/log/wormhole`
- 用途：容器内日志根目录，后台、FreeRADIUS、MariaDB 和日志轮转都会用到。
- 建议：一般无需修改。

### `LOG_RETENTION_DAYS`

- 默认值：`7`
- 用途：日志保留天数，供日志轮转组件使用。
- 建议：磁盘紧张可调小，审计需求高可适当调大。

## 数据库

### `DB_PORT`

- 默认值：`3306`
- 用途：后台和 `FreeRADIUS` 连接数据库时使用的端口。
- 建议：单机部署通常保持默认。

### `DB_NAME`

- 默认值：`radius`
- 用途：MariaDB 初始化和业务访问使用的数据库名。
- 建议：一般保持默认。

### `DB_USER`

- 默认值：`radius`
- 用途：后台和 `FreeRADIUS` 使用的数据库用户名。
- 建议：一般保持默认。

### `DB_PASSWORD`

- 默认值：`change-me-db-password`
- 用途：后台和 `FreeRADIUS` 使用的数据库密码。
- 必改：是
- 建议：使用高强度随机密码。

### `MARIADB_ROOT_PASSWORD`

- 默认值：`change-me-root-password`
- 用途：MariaDB `root` 密码，主要用于初始化、排障和手工运维。
- 必改：是

### `MYSQL_GENERAL_LOG`

- 默认值：`OFF`
- 用途：控制 MariaDB 通用查询日志是否开启。
- 常见取值：`ON`、`OFF`
- 建议：默认关闭，排查 SQL 时临时开启。

### `MYSQL_SLOW_LOG_THRESHOLD_MS`

- 默认值：`1000`
- 用途：MariaDB 慢查询阈值，单位毫秒。
- 建议：想更早发现慢查询可以适当调低。

## RADIUS

### `RADIUS_SHARED_SECRET`

- 默认值：`change-me-radius-secret`
- 用途：`ipsec-l2tp-gateway` 与 `FreeRADIUS` 之间的共享密钥。
- 必改：是
- 常见问题：两端不一致时会导致鉴权失败。

## 管理后台

### `ADMIN_PORTAL_PORT`

- 默认值：`8080`
- 用途：宿主机暴露给管理员访问的后台端口。
- 示例：`http://127.0.0.1:8080`
- 建议：如果宿主机 `8080` 被占用，可以改成别的端口。

### `ADMIN_USERNAME`

- 默认值：`admin`
- 用途：初始化管理员用户名。
- 建议：自用场景可保持默认，多人共用建议修改。

### `ADMIN_PASSWORD`

- 默认值：`change-me-admin-password`
- 用途：初始化管理员密码。
- 必改：建议是

### `ADMIN_SESSION_SECRET`

- 默认值：`change-me-session-secret-minimum-32-chars`
- 用途：后台登录态 Cookie 的签名密钥。
- 必改：是
- 建议：至少使用 32 位随机字符串。

## VPN 业务默认值

### `VPN_SHARED_PSK`

- 默认值：`change-me-shared-psk`
- 用途：客户端连接 `L2TP/IPSec` 时使用的共享密钥。
- 必改：是
- 常见问题：值错误时通常无法完成隧道建立。

### `VPN_DEFAULT_SPEED_PROFILE`

- 默认值：`standard-10m`
- 用途：新建账号时默认分配的限速档位。
- 注意：该名称必须在数据库已有的限速档位中存在。

### `VPN_MAX_CONCURRENT_SESSIONS`

- 默认值：`1`
- 用途：新建账号时默认允许的最大并发会话数。
- 建议：单人单号场景保持 `1` 最稳妥。

### `VPN_GATEWAYS`

- 默认值：JSON 数组
- 用途：后台展示和导出的接入点列表。
- 必改：是

示例：

```json
[{"name":"primary","address":"203.0.113.10","protocol":"l2tp-ipsec-psk","port":1701,"priority":1,"notes":"primary gateway"}]
```

字段说明：

- `name`：接入点名称
- `address`：客户端实际连接的公网地址或域名
- `protocol`：当前应填写 `l2tp-ipsec-psk`
- `port`：接入端口，通常为 `1701`
- `priority`：排序优先级，数值越小越靠前
- `notes`：备注信息

常见问题：

- `address` 填成内网地址，外部客户端无法连接
- JSON 格式错误会导致启动或解析失败
- 多个网关优先级混乱会影响导出顺序

## VPN 网络与协议

### `VPN_IPSEC_IKE_PORT`

- 默认值：`500`
- 用途：`strongSwan` 使用的 IKE UDP 端口。
- 建议：一般保持默认。

### `VPN_IPSEC_NATT_PORT`

- 默认值：`4500`
- 用途：`strongSwan` 使用的 NAT-T UDP 端口。
- 建议：一般保持默认。

### `VPN_IPSEC_LOCAL_ID`

- 默认值：空
- 用途：显式指定 `strongSwan` 在 IKEv1 主模式里对外声明的本端身份。
- 建议：如果部署机只有内网地址、通过公网 EIP/NAT 对外提供服务，这里应设置为客户端实际连接的公网 IP 或域名。
- 常见问题：不设置时，`strongSwan` 可能使用宿主机内网 IP 作为本端身份；某些原生 `L2TP/IPSec PSK` 客户端会在首次可用后、断线重连时卡在 IKE 第 1 阶段最后一步。

### `VPN_L2TP_PORT`

- 默认值：`1701`
- 用途：`accel-ppp` 暴露的 L2TP UDP 端口。
- 建议：一般保持默认。

### `VPN_RADIUS_AUTH_PORT`

- 默认值：`1812`
- 用途：网关向 `FreeRADIUS` 发送鉴权请求时使用的端口。
- 建议：一般保持默认。

### `VPN_RADIUS_ACCT_PORT`

- 默认值：`1813`
- 用途：网关向 `FreeRADIUS` 发送记账请求时使用的端口。
- 建议：一般保持默认。

### `VPN_NAS_IDENTIFIER`

- 默认值：`wormhole-l2tp`
- 用途：写入 RADIUS 记录的 NAS 标识。
- 建议：单机部署通常保持默认；多节点可改成更有辨识度的名字。

### `VPN_NAS_IP_ADDRESS`

- 默认值：`127.0.0.1`
- 用途：写入 RADIUS 记录中的 NAS IP。
- 建议：如果依赖该字段做多节点区分，可改成更明确的地址。

### `VPN_NETWORK`

- 默认值：`10.88.0.0`
- 用途：VPN 客户端地址池网段。
- 补充：`ipsec-l2tp-gateway` 会基于它和 `VPN_NETMASK`、`VPN_GATEWAY_IP` 自动生成 `accel-ppp` 的客户端地址池，并自动排除网关地址。
- 建议：避免与办公网、宿主机局域网或常见家庭网段冲突。

### `VPN_NETMASK`

- 默认值：`255.255.255.0`
- 用途：VPN 客户端地址池掩码。
- 建议：与 `VPN_NETWORK` 配套设置。

### `VPN_GATEWAY_IP`

- 默认值：`10.88.0.1`
- 用途：分配给客户端的 PPP 网关地址。
- 补充：该地址会从 `accel-ppp` 客户端地址池中自动排除，不能与客户端分配范围重叠。
- 建议：应位于 `VPN_NETWORK` 对应网段内。

### `VPN_DNS_1`

- 默认值：`1.1.1.1`
- 用途：下发给客户端的主 DNS。
- 建议：如果有内网解析需求，改成自己的 DNS。

### `VPN_DNS_2`

- 默认值：`8.8.8.8`
- 用途：下发给客户端的备用 DNS。
- 建议：如果有内网解析需求，改成自己的 DNS。

### `VPN_MTU`

- 默认值：`1400`
- 用途：PPP 的 `MTU/MRU` 设置。
- 建议：一般保持默认，只有在特定网络环境下出现分片或访问异常时再调整。

### `VPN_NAT_DEVICE`

- 默认值：`eth0`
- 用途：网关容器内用于 NAT 的出口网卡。
- 必查：是
- 常见问题：配置错误时最常见现象是“能连接，但没有流量”。

## 推荐最小修改集

```dotenv
DB_PASSWORD=随机强密码
MARIADB_ROOT_PASSWORD=另一组随机强密码
RADIUS_SHARED_SECRET=随机强密钥
ADMIN_PASSWORD=强密码
ADMIN_SESSION_SECRET=长度至少32位的随机字符串
VPN_SHARED_PSK=客户端共享密钥
VPN_GATEWAYS=[{"name":"primary","address":"你的公网IP或域名","protocol":"l2tp-ipsec-psk","port":1701,"priority":1,"notes":"primary"}]
VPN_NAT_DEVICE=你的实际出口网卡名
```

## 常见误配

- 忘记修改默认密码或默认密钥
- `VPN_GATEWAYS` JSON 格式错误，或里面填的是内网地址
- `RADIUS_SHARED_SECRET` 两端不一致
- `VPN_NAT_DEVICE` 不是实际出口网卡
- VPN 地址池与现有网络冲突
