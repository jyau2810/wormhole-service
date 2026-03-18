# 运维指南

英文原版请见 [OPERATIONS.md](/Users/yaoji/Documents/Workspace/wormhole-service/docs/OPERATIONS.md)。

## 管理员登录

后台管理员账号由以下环境变量初始化：

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`

每次容器启动时，后台都会确保该管理员存在，并用 `.env` 中的密码重新同步密码哈希。

## 日志文件

优先查看 `var/log/` 下的文件日志：

- `var/log/admin-portal/app.log`
- `var/log/admin-portal/access.log`
- `var/log/admin-portal/error.log`
- `var/log/ca-api/app.log`
- `var/log/ca-api/access.log`
- `var/log/ca-api/error.log`
- `var/log/freeradius/freeradius.log`
- `var/log/ocserv/ocserv.log`
- `var/log/ocserv/error.log`
- `var/log/mariadb/error.log`
- `var/log/mariadb/slow.log`

日志由 `logrotate` sidecar 保留 7 天。

## 常见操作

### 创建 VPN 账号

在后台中：

1. 输入 `username`
2. 输入 VPN 密码
3. 选择到期日期
4. 提交

后台会写入：

- `vpn_accounts`
- `radcheck` 的 `Crypt-Password`
- `radcheck` 的 `Expiration`

### 延长账号有效期

打开账号详情页，提交新的到期日期即可。

不需要重签发设备证书。

### 禁用或启用账号

在账号页面使用开关按钮。

- `enabled`：恢复配置中的到期时间
- `disabled`：立即把有效 RADIUS 到期时间压到当前时刻

### 签发设备证书

在账号页面：

1. 输入设备标识
2. 点击 `Issue Device Certificate`

如果两个设备槽位都被占用，后台会拒绝签发。

### 吊销设备证书

在账号页面点击 `Revoke`。

这会：

- 把数据库记录标记为已吊销
- 重新生成 CRL
- 释放设备槽位供后续复用

## 备份

需要备份：

- MariaDB 卷
- `ca-data` 卷
- `.env`

推荐命令：

```bash
docker compose exec db mysqldump -u root -p"$MARIADB_ROOT_PASSWORD" "$MARIADB_DATABASE" > backup.sql
docker run --rm -v wormhole-vpn_ca-data:/from -v "$PWD":/to alpine sh -c 'cd /from && tar czf /to/ca-data.tgz .'
```

## 恢复

恢复顺序：

1. 停止整套服务
2. 恢复 MariaDB 数据或导入 `backup.sql`
3. 恢复 `ca-data` 卷
4. 重新启动服务

恢复 CA 卷非常关键。否则历史签发的设备证书将不再匹配当前 CA 和 CRL 状态。

## 常用命令

```bash
docker compose logs -f admin-portal
docker compose logs -f ca-api
docker compose logs -f freeradius
docker compose logs -f ocserv
docker compose exec ocserv occtl show users
tail -f var/log/admin-portal/app.log
tail -f var/log/ca-api/error.log
tail -f var/log/freeradius/freeradius.log
```
