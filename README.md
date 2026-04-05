# Wormhole Access Stack

这是一个面向小规模远程接入账号分发场景的 Docker 化 VPN 控制平面，当前方案以 `L2TP/IPSec PSK` 为主通道，配合 `FreeRADIUS + MariaDB + 管理后台` 提供账号管理、认证鉴权、会话审计、限速控制和异常事件观察能力。

当前仓库适合的场景：

- 为 `macOS / Windows / iPhone / Android 12 以下` 提供原生 `L2TP/IPSec PSK` 接入
- 统一管理账号有效期、并发数和带宽档位
- 在后台查看接入点、共享密钥、在线会话、认证日志和异常事件
- 为后续外接 `UniConnect SSL VPN` 预留统一账号与配置导出能力

不在当前仓库范围内的内容：

- `UniConnect SSL VPN` 兼容网关本体
- 大规模多地域高可用部署
- 专门的密钥托管与企业级机密管理

## 文档

- [环境变量说明](/Users/jyau/Documents/Projects/wormhole-service/docs/ENV.md)
- [技术文档](/Users/jyau/Documents/Projects/wormhole-service/docs/ARCHITECTURE.md)
- [排障文档](/Users/jyau/Documents/Projects/wormhole-service/docs/TROUBLESHOOTING.md)

## 架构概览

核心组件如下：

- `ipsec-l2tp-gateway`：基于 `strongSwan + accel-ppp` 提供 `IPSec + L2TP/PPP`
- `freeradius`：负责鉴权、到期控制、并发控制和回复限速属性
- `db`：基于 `MariaDB` 存储账号、限速档位、认证日志、会话与异常事件
- `admin-portal`：负责账号管理、接入点展示、连接参数导出和运维观察
- `logrotate`：负责日志轮转

关键认证模型：

1. 客户端使用网关级共享密钥 `VPN_SHARED_PSK`
2. 用户使用账号级用户名和密码
3. 网关通过 `RADIUS_SHARED_SECRET` 与 `FreeRADIUS` 交互
4. `FreeRADIUS` 从数据库读取 `NT-Password`、到期时间、并发限制和限速属性

## 部署说明

### 宿主机前置条件

准备一台 `Ubuntu 22.04` 或 `Debian 12` 宿主机，并满足：

- `Docker 26+`
- `Docker Compose` 插件
- Linux 宿主机可用 `host network`
- `/dev/net/tun` 可用
- `/dev/ppp` 可用
- 公网已放行 `500/udp`、`4500/udp`、`1701/udp`
- 宿主机本地 `1812/udp`、`1813/udp` 未被其他服务占用

可先执行：

```bash
docker --version
docker compose version
ls -l /dev/net/tun /dev/ppp
```

### 开启 IPv4 转发

```bash
sudo sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-wormhole-vpn.conf
sudo sysctl --system
```

### 配置环境变量

```bash
cp .env.example .env
```

详细解释见 [环境变量说明](/Users/jyau/Documents/Projects/wormhole-service/docs/ENV.md)。

至少需要修改以下变量：

- `DB_PASSWORD`
- `MARIADB_ROOT_PASSWORD`
- `RADIUS_SHARED_SECRET`
- `ADMIN_PASSWORD`
- `ADMIN_SESSION_SECRET`
- `VPN_SHARED_PSK`
- `VPN_GATEWAYS`

常用变量分组如下：

`数据库`

- `DB_PORT`、`DB_NAME`、`DB_USER`、`DB_PASSWORD`
- `MARIADB_ROOT_PASSWORD`

`后台`

- `APP_TIMEZONE`
- `ADMIN_PORTAL_PORT`
- `ADMIN_USERNAME`、`ADMIN_PASSWORD`、`ADMIN_SESSION_SECRET`
- `VPN_SHARED_PSK`
- `VPN_DEFAULT_SPEED_PROFILE`
- `VPN_MAX_CONCURRENT_SESSIONS`
- `VPN_GATEWAYS`

`VPN 网关`

- `VPN_IPSEC_IKE_PORT`、`VPN_IPSEC_NATT_PORT`、`VPN_L2TP_PORT`
- `VPN_RADIUS_AUTH_PORT`、`VPN_RADIUS_ACCT_PORT`
- `VPN_NAS_IDENTIFIER`、`VPN_NAS_IP_ADDRESS`
- `VPN_NETWORK`、`VPN_NETMASK`、`VPN_GATEWAY_IP`
- `VPN_DNS_1`、`VPN_DNS_2`
- `VPN_MTU`
- `VPN_NAT_DEVICE`
- `RADIUS_SHARED_SECRET`

如果宿主机外网口不是 `eth0`，同步修改 `VPN_NAT_DEVICE`。

### 网关网络模式说明

`ipsec-l2tp-gateway` 默认使用宿主机网络而不是 Docker bridge 端口映射。

- 客户端连接方式不变，仍然使用原生 `L2TP/IPSec PSK`
- `VPN_GATEWAYS`、共享密钥、账号密码、DNS 和后台导出内容都无需修改
- 这样做是为了避免 `NAT-T + IPsec transport mode` 下内层 `L2TP` 流量无法稳定进入 `PPP`
- 对应地，`freeradius` 会仅在部署机回环地址开放 `1812/udp` 和 `1813/udp`，供网关通过 `127.0.0.1` 访问

这套完整 VPN 数据面部署以 Linux 宿主机为目标；`macOS` 本机联调仍建议只跑控制平面服务。

### 启动服务

```bash
docker compose --env-file .env up -d --build
```

预期服务：

- `db`
- `freeradius`
- `admin-portal`
- `ipsec-l2tp-gateway`
- `logrotate`

### 健康检查

```bash
docker compose ps
ss -lunp | grep -E ':(500|4500|1701|1812|1813)\s'
docker compose logs --tail=50 freeradius
docker compose logs --tail=50 ipsec-l2tp-gateway
docker compose exec ipsec-l2tp-gateway ipsec statusall
docker compose exec ipsec-l2tp-gateway sh -c 'ip xfrm state; echo; ip xfrm policy'
tail -n 50 var/log/gateway/accel-ppp.log
docker compose logs --tail=50 admin-portal
```

后台默认地址：

```text
http://127.0.0.1:${ADMIN_PORTAL_PORT}
```

### 从当前电脑访问远程部署机后台

当前 `docker-compose.yml` 默认把后台只绑定在部署机本地回环地址：

```text
127.0.0.1:${ADMIN_PORTAL_PORT}:8000
```

这意味着不能直接在浏览器里访问 `http://服务器公网IP:${ADMIN_PORTAL_PORT}`。推荐通过 SSH 隧道从当前电脑安全访问：

```bash
ssh -L 18080:127.0.0.1:${ADMIN_PORTAL_PORT} root@YOUR_SERVER_IP
```

建立隧道后，在当前电脑浏览器中打开：

```text
http://127.0.0.1:18080
```

如果沿用当前示例配置，命令可写成：

```bash
ssh -L 18080:127.0.0.1:8080 root@43.156.147.242
```

然后在当前电脑访问：

```text
http://127.0.0.1:18080
```

如果你明确希望直接通过公网访问后台，需要自行修改端口绑定策略、放行对应防火墙端口，并额外做好访问控制；默认配置不建议这样做。

### 首次联调

1. 登录后台创建测试账号。
2. 在账号详情页确认共享密钥、接入点和限速档位。
3. 在 `macOS / Windows / iPhone / Android 12 以下` 使用原生 `L2TP/IPSec PSK` 接入。
4. 使用后台导出的 JSON 配置校验网关列表。
5. 连接后观察后台中的会话、流量和异常事件。

## 本机开发联调

在 `macOS` 上建议仅联调控制平面服务，不验证完整 VPN 数据面：

```bash
cp .env.example .env
make local-up
make local-smoke
make local-down
```

该模式覆盖：

- `db`
- `freeradius`
- `admin-portal`
- `logrotate`

该模式不覆盖：

- `ipsec-l2tp-gateway`
- `PPP` 转发
- `IPSec` 隧道
- `NAT` 与完整出网

## 交付内容

- `docker-compose.yml`：整套服务入口
- `.env.example`：环境变量样例
- `bootstrap/db`：数据库初始化结构
- `images/ipsec-l2tp-gateway`：`strongSwan + accel-ppp` 网关镜像
- `images/freeradius`：RADIUS 鉴权与记账服务
- `images/admin-portal`：账号、会话、流量和异常事件后台

## 运维与排障入口

常用日志与命令：

```bash
docker compose logs -f admin-portal
docker compose logs -f freeradius
docker compose logs -f ipsec-l2tp-gateway
docker compose exec ipsec-l2tp-gateway ipsec statusall
docker compose exec ipsec-l2tp-gateway sh -c 'ip xfrm state; echo; ip xfrm policy'
ss -lunp | grep -E ':(500|4500|1701|1812|1813)\s'
tail -f var/log/gateway/accel-ppp.log
docker compose exec db mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" radius
```

建议日常关注：

- 后台未处理异常事件
- 失败认证频繁的账号
- `VPN_GATEWAYS` 是否仍与公网接入点一致

更详细的技术说明与排障步骤见：

- [环境变量说明](/Users/jyau/Documents/Projects/wormhole-service/docs/ENV.md)
- [技术文档](/Users/jyau/Documents/Projects/wormhole-service/docs/ARCHITECTURE.md)
- [排障文档](/Users/jyau/Documents/Projects/wormhole-service/docs/TROUBLESHOOTING.md)
