# 运维说明

英文原版请见 [OPERATIONS.md](/Users/jyau/Documents/Projects/wormhole-service/docs/OPERATIONS.md)。

## 后台日常操作

管理后台负责：

- 创建 VPN 账号
- 改密
- 续期
- 调整限速档位
- 调整最大并发会话数
- 禁用异常账号

## 重点日志

- `var/log/admin-portal/app.log`
- `var/log/admin-portal/access.log`
- `var/log/freeradius/freeradius.log`
- `var/log/gateway/accel-ppp.log`
- `var/log/mariadb/error.log`

## 常用命令

```bash
docker compose logs -f admin-portal
docker compose logs -f freeradius
docker compose logs -f ipsec-l2tp-gateway
docker compose exec db mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" radius
```

## 日常巡检

- 查看后台未处理异常事件。
- 检查失败认证频繁的账号。
- 核对 `VPN_GATEWAYS` 是否仍与公网接入点一致。
