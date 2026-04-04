# 部署指南

英文原版请见 [DEPLOY.md](/Users/jyau/Documents/Projects/wormhole-service/docs/DEPLOY.md)。

## 1. 宿主机前置条件

准备一台 Ubuntu 22.04 或 Debian 12 宿主机，并满足：

- Docker 26+
- Docker Compose 插件
- `/dev/net/tun` 可用
- `/dev/ppp` 可用
- 公网已放行 `500/udp`、`4500/udp`、`1701/udp`

检查命令：

```bash
docker --version
docker compose version
ls -l /dev/net/tun /dev/ppp
```

## 2. 开启宿主机转发

```bash
sudo sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-wormhole-vpn.conf
sudo sysctl --system
```

## 3. 配置环境变量

```bash
cp .env.example .env
```

至少要修改：

- `MARIADB_PASSWORD`
- `MARIADB_ROOT_PASSWORD`
- `RADIUS_SHARED_SECRET`
- `ADMIN_PASSWORD`
- `ADMIN_SESSION_SECRET`
- `VPN_SHARED_PSK`
- `VPN_GATEWAYS`

如果你的网关在宿主机外网口不是 `eth0`，同步修改 `VPN_NAT_DEVICE`。

## 4. 启动服务

```bash
docker compose --env-file .env up -d --build
```

预期服务：

- `db`
- `freeradius`
- `admin-portal`
- `ipsec-l2tp-gateway`
- `logrotate`

## 5. 健康检查

```bash
docker compose ps
docker compose logs --tail=50 freeradius
docker compose logs --tail=50 ipsec-l2tp-gateway
docker compose logs --tail=50 admin-portal
```

后台默认地址：

```text
http://127.0.0.1:${ADMIN_PORTAL_PORT}
```

## 6. 首次联调

1. 登录后台创建测试账号。
2. 在账号详情页确认共享密钥、接入点和限速档位。
3. 在 `macOS / Windows / iPhone / Android 12 以下` 选择 `L2TP/IPSec PSK` 原生方式接入。
4. 使用后台导出的 JSON 配置校验网关列表。
5. 连接后观察后台会话、流量和异常事件面板。

## 7. Android 12+ 说明

本仓库当前不实现 UniConnect 兼容 SSL 网关。

- 后台会保留统一账号体系和标准化网关配置导出。
- 后续接入外部 UniConnect SSL 网关时，应复用当前 RADIUS 与账号表。
