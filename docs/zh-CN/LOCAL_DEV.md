# 本机开发联调

英文原版请见 [LOCAL_DEV.md](/Users/yaoji/Documents/Workspace/wormhole-service/docs/LOCAL_DEV.md)。

## 范围

macOS 本机联调仅覆盖非 VPN 数据面验证。

本模式会启动：

- `db`
- `ca-api`
- `freeradius`
- `admin-portal`
- `logrotate`

本模式不会启动：

- `ocserv`

不要把 macOS 本机联调结果当成 TUN、NAT 或完整 VPN 转发已经验证通过。

## 命令

```bash
cp .env.example .env
make local-up
make local-smoke
make local-down
```

## `local-smoke` 会验证什么

- 管理后台健康检查接口
- 从容器内访问的 CA API 健康检查接口
- 通过 `radtest` 完成的 FreeRADIUS 密码认证
- 写入 `radcheck` 的数据库路径

## 本机日志

所有文件日志都写入：

```text
var/log/
```

重点路径：

- `var/log/admin-portal/app.log`
- `var/log/admin-portal/access.log`
- `var/log/admin-portal/error.log`
- `var/log/ca-api/app.log`
- `var/log/freeradius/freeradius.log`
- `var/log/mariadb/error.log`
