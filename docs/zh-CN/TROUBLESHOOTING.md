# 故障排查

英文原版请见 [TROUBLESHOOTING.md](/Users/yaoji/Documents/Workspace/wormhole-service/docs/TROUBLESHOOTING.md)。

## `docker: command not found`

宿主机还没有安装 Docker。先安装 Docker 和 Compose 插件。

## `Cannot open TUN/TAP dev`

宿主机缺少 `/dev/net/tun`，或者容器运行时没有把它透传进去。

检查：

```bash
ls -l /dev/net/tun
docker compose ps
```

## VPN 已连接但无法访问互联网

检查宿主机转发：

```bash
sysctl net.ipv4.ip_forward
```

检查 ocserv 容器内 NAT 规则：

```bash
docker compose exec ocserv iptables -t nat -S
docker compose exec ocserv iptables -S FORWARD
```

如果你的出口网卡不是 `eth0`，请在 `.env` 中把 `OCSERV_NAT_DEVICE` 改成正确值。

## 管理后台能打开但登录失败

启动后 `.env` 中的 `ADMIN_PASSWORD` 是真实来源。如果你修改了 `.env`，需要重建后台容器：

```bash
docker compose up -d --build admin-portal
```

## 账号存在但 VPN 登录被拒绝

先看 FreeRADIUS 文件日志：

```bash
tail -n 100 var/log/freeradius/freeradius.log
```

再检查生成的 `radcheck` 记录：

```bash
docker compose exec db mariadb -u root -p"$MARIADB_ROOT_PASSWORD" "$MARIADB_DATABASE" -e \
'SELECT username, attribute, op, value FROM radcheck ORDER BY username, attribute;'
```

## 设备包可导入，但证书登录仍失败

常见原因：

- 设备证书已经被吊销
- CRL 已更新，但客户端仍在使用旧证书
- 账号密码错误
- 账号已过期或被禁用

检查：

- 后台中的认证历史
- `var/log/ca-api/error.log`
- `var/log/ocserv/error.log`

## 应用报错但 `docker logs` 看起来为空

本方案主要把服务日志写到 `var/log/` 下的文件。

优先查看对应文件：

- 管理后台：`var/log/admin-portal/error.log`
- CA API：`var/log/ca-api/error.log`
- FreeRADIUS：`var/log/freeradius/freeradius.log`
- ocserv：`var/log/ocserv/error.log`
- MariaDB：`var/log/mariadb/error.log`

## 不能签发第 3 台设备

这是预期行为。每个账号最多只能有 2 个有效设备槽位。

先吊销 1 台已有设备，再签发替换设备。
