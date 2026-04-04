# 排障文档

## 先看哪些地方

排障时优先确认三类信息：

- 基础环境是否满足：端口、防火墙、`/dev/net/tun`、`/dev/ppp`、宿主机转发
- 认证链路是否正常：网关日志、`FreeRADIUS` 日志、`radcheck`、`radpostauth`
- 会话与流量是否正常：`radacct`、后台会话面板、异常事件记录

常用命令：

```bash
docker compose ps
docker compose logs --tail=100 ipsec-l2tp-gateway
docker compose logs --tail=100 freeradius
docker compose logs --tail=100 admin-portal
docker compose exec db mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" radius
```

## 当前电脑打不开远程部署机后台

先确认当前设计是否符合预期：

- 后台默认只绑定在部署机的 `127.0.0.1:${ADMIN_PORTAL_PORT}`
- 因此不能直接在当前电脑访问 `http://服务器公网IP:${ADMIN_PORTAL_PORT}`

推荐做法是使用 SSH 隧道：

```bash
ssh -L 18080:127.0.0.1:8080 root@43.156.147.242
```

然后在当前电脑浏览器打开：

```text
http://127.0.0.1:18080
```

如果仍然打不开，依次检查：

- SSH 是否能正常登录部署机
- 部署机上 `admin-portal` 是否已启动
- `ADMIN_PORTAL_PORT` 是否与 `.env` 中一致
- 是否误把浏览器地址写成了服务器公网 IP

部署机上可执行：

```bash
docker compose --env-file .env ps
docker compose --env-file .env logs --tail=100 admin-portal
ss -lntp | grep 8080
```

## 原生 L2TP 客户端无法连接

先检查：

- 宿主机是否放行 `500/udp`、`4500/udp`、`1701/udp`
- `/dev/net/tun` 和 `/dev/ppp` 是否可用
- 宿主机是否已开启 `net.ipv4.ip_forward=1`
- 客户端填写的 `VPN_SHARED_PSK` 是否正确
- `VPN_GATEWAYS` 中下发的地址是否为真实公网接入点

再查看：

```bash
docker compose logs --tail=100 ipsec-l2tp-gateway
docker compose logs --tail=100 freeradius
```

排查思路：

- 如果 `ipsec-l2tp-gateway` 没有握手相关日志，优先检查端口放行和公网地址
- 如果 `IPSec` 成功但 `PPP/L2TP` 没有建立，优先检查 `accel-ppp`、`/dev/ppp` 和网关配置
- 如果开始进入认证阶段但被拒绝，转到“账号存在但认证被拒绝”

## 账号存在但认证被拒绝

先看后台中的最近认证记录，再检查数据库中的 `radcheck`：

```bash
docker compose exec db mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" radius -e \
  "SELECT username, attribute, value FROM radcheck WHERE username='YOUR_USER';"
```

确认至少存在：

- `NT-Password`
- `Expiration`
- `Simultaneous-Use`

同时检查：

- 账号是否已被后台禁用
- 到期时间是否早于当前时间
- 并发限制是否已被现有会话占满
- `RADIUS_SHARED_SECRET` 是否与网关配置一致

如果 `radcheck` 数据正确但仍失败，继续查看：

```bash
docker compose logs --tail=200 freeradius
```

重点关注：

- 用户名是否被正确传入
- `NT-Password` 是否同步成功
- 失败原因是密码错误、到期、并发超限还是属性缺失

## 连接成功但没有流量

优先检查：

- 宿主机 NAT 是否正常
- `VPN_NAT_DEVICE` 是否指向正确外网网卡
- 地址池、网关地址和掩码是否配置正确
- DNS 下发是否符合预期

建议同时查看：

```bash
docker compose logs --tail=100 ipsec-l2tp-gateway
docker compose exec db mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" radius -e \
  "SELECT username, acctstarttime, acctstoptime, acctinputoctets, acctoutputoctets FROM radacct ORDER BY radacctid DESC LIMIT 20;"
```

判断方式：

- 有会话但长期没有流量增长，优先怀疑 NAT、转发或客户端路由
- 有输入无输出或有输出无输入，优先检查出口网卡和上游网络限制

## 流量或异常事件不准确

重点检查：

- `radacct` 是否收到 `interim update`
- 网关上报的 `NAS IP` 和标识是否正确
- 账号绑定的限速档位是否符合预期
- 后台是否能持续读取最新会话和日志数据

可先执行：

```bash
docker compose exec db mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" radius -e \
  "SELECT username, acctsessionid, acctstarttime, acctupdatetime, acctinputoctets, acctoutputoctets FROM radacct ORDER BY acctupdatetime DESC LIMIT 20;"
```

如果异常事件偏多，优先核对：

- 是否存在多个网关重复上报同一账号
- 是否有测试脚本在短时间内重复失败登录
- 当前限速档位是否过低，导致阈值判断过于敏感
