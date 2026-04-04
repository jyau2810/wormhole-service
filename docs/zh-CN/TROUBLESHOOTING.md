# 排障说明

英文原版请见 [TROUBLESHOOTING.md](/Users/jyau/Documents/Projects/wormhole-service/docs/TROUBLESHOOTING.md)。

## 原生 L2TP 客户端无法连接

先检查：

- 宿主机是否放行 `500/udp`、`4500/udp`、`1701/udp`
- `/dev/net/tun` 和 `/dev/ppp` 是否可用
- 客户端填写的 `VPN_SHARED_PSK` 是否正确

再查看：

```bash
docker compose logs --tail=100 ipsec-l2tp-gateway
docker compose logs --tail=100 freeradius
```

## 账号存在但认证被拒绝

先看后台中的最近认证记录，再检查数据库中的 `radcheck`：

```bash
docker compose exec db mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" radius -e \
  "SELECT username, attribute, value FROM radcheck WHERE username='YOUR_USER';"
```

确认存在：

- `NT-Password`
- `Expiration`
- `Simultaneous-Use`

## 流量或异常事件不准确

重点检查：

- `radacct` 是否收到 interim update
- 网关上报的 NAS IP 和标识是否正确
- 账号绑定的限速档位是否符合预期
