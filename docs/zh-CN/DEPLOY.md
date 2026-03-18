# 部署指南

英文原版请见 [DEPLOY.md](/Users/yaoji/Documents/Workspace/wormhole-service/docs/DEPLOY.md)。

## 1. 宿主机前置条件

准备一台 Ubuntu 22.04 宿主机，并满足：

- Docker 26
- Docker Compose 插件
- `/dev/net/tun` 可用
- 公网已放行 `443/tcp` 和 `443/udp`

在宿主机执行以下检查：

```bash
docker --version
docker compose version
ls -l /dev/net/tun
```

## 2. 开启宿主机转发

在宿主机上开启 IPv4 转发：

```bash
sudo sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-wormhole-vpn.conf
sudo sysctl --system
```

## 3. 防火墙与安全组

放行：

- `443/tcp`
- `443/udp`

不要把管理后台直接暴露到公网。默认它只绑定到 `127.0.0.1:${ADMIN_PORTAL_PORT}`。

推荐访问方式：

- SSH 隧道
- Tailscale/ZeroTier 等侧带网络
- 带 IP 白名单和 TLS 的反向代理

## 4. 配置环境变量

从样例生成 `.env`：

```bash
cp .env.example .env
```

至少要替换：

- `MARIADB_PASSWORD`
- `MARIADB_ROOT_PASSWORD`
- `RADIUS_SHARED_SECRET`
- `ADMIN_PASSWORD`
- `ADMIN_SESSION_SECRET`
- `CA_API_TOKEN`
- `VPN_SERVER_HOST`
- 同时检查 `LOG_LEVEL`、`LOG_RETENTION_DAYS`、`MYSQL_GENERAL_LOG`、`MYSQL_SLOW_LOG_THRESHOLD_MS`

## 5. 启动服务

```bash
docker compose --env-file .env up -d --build
```

预期服务：

- `db`
- `ca-api`
- `freeradius`
- `admin-portal`
- `ocserv`

## 6. 健康检查

```bash
docker compose ps
docker compose logs --tail=50 ca-api
docker compose logs --tail=50 freeradius
docker compose logs --tail=50 ocserv
```

主要文件日志同时写入：

```text
var/log/
```

管理后台默认地址：

```text
http://127.0.0.1:${ADMIN_PORTAL_PORT}
```

如果你是远程连接服务器：

```bash
ssh -L 8080:127.0.0.1:${ADMIN_PORTAL_PORT} user@your-server
```

然后打开 `http://127.0.0.1:8080`。

## 7. 首次操作检查

登录后台后：

1. 创建一个测试 VPN 账号
2. 签发 1 台设备证书
3. 下载 ZIP 包
4. 将 `client.p12` 导入支持 OpenConnect 的客户端
5. 使用后台显示的 VPN 用户名和密码登录

## 8. 生产前补充动作

在正式发给真实用户之前：

- 给 `VPN_SERVER_HOST` 配好域名
- 用公网证书替换自动生成的服务端证书
- 用来源 IP 白名单限制后台访问
- 启用自动备份
- 如果接入集中式日志系统，把 `var/log/` 纳入采集范围
