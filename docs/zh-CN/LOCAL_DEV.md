# 本机开发联调

英文原版请见 [LOCAL_DEV.md](/Users/jyau/Documents/Projects/wormhole-service/docs/LOCAL_DEV.md)。

## 范围

macOS 本机联调仅覆盖控制平面服务：

- `db`
- `freeradius`
- `admin-portal`
- `logrotate`

本模式不验证：

- `ipsec-l2tp-gateway`
- PPP 转发
- IPSec 隧道
- NAT 与完整出网

## 命令

```bash
cp .env.example .env
make local-up
make local-smoke
make local-down
```

## `local-smoke` 会验证什么

- 管理后台健康检查
- 写入 `radcheck` 的数据库路径
- 使用 `NT-Password` 的 `MSCHAP` RADIUS 认证
