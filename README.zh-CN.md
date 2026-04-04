# Wormhole Access Stack

中文文档入口。英文原版请见 [README.md](/Users/jyau/Documents/Projects/wormhole-service/README.md)。

这是一个面向小规模远程接入账号分发场景的 Docker 化 VPN 控制平面，当前实现包含：

- `L2TP/IPSec PSK` 主通道，面向 `macOS / Windows / iPhone / Android 12 以下`
- `FreeRADIUS` 统一账号认证、会话审计与流量统计
- 按账号控制有效期、并发数和限速档位
- 后台展示接入点、共享密钥、在线会话、认证日志和异常事件
- 预留 `UniConnect SSL VPN` 外部网关接入面，不在本仓库内实现兼容网关

## 快速开始

1. 复制 `.env.example` 为 `.env`，填入数据库密码、RADIUS 密钥和 `VPN_SHARED_PSK`。
2. 根据你的公网接入点修改 `VPN_GATEWAYS`。
3. 阅读 [docs/zh-CN/DEPLOY.md](/Users/jyau/Documents/Projects/wormhole-service/docs/zh-CN/DEPLOY.md) 完成宿主机准备。
4. 启动整套服务：

```bash
docker compose --env-file .env up -d --build
```

5. 访问后台 `http://127.0.0.1:${ADMIN_PORTAL_PORT}`，创建账号后进入账号详情页查看连接参数和 JSON 配置导出。

## 本机非 VPN 联调

在 macOS 上，建议只联调 `db / freeradius / admin-portal` 这些非 VPN 数据面服务：

```bash
cp .env.example .env
make local-up
make local-smoke
```

完整 L2TP/IPSec 转发、NAT 与 PPP 数据面仍需在 Linux 宿主机验证。

## 文档索引

- [env.zh-CN.md](/Users/jyau/Documents/Projects/wormhole-service/env.zh-CN.md)
- [docs/zh-CN/DEPLOY.md](/Users/jyau/Documents/Projects/wormhole-service/docs/zh-CN/DEPLOY.md)
- [docs/zh-CN/ARCHITECTURE.md](/Users/jyau/Documents/Projects/wormhole-service/docs/zh-CN/ARCHITECTURE.md)

## 交付内容

- `docker-compose.yml`：部署入口
- `.env.example`：L2TP/IPSec 与后台所需环境变量样例
- `bootstrap/db`：MariaDB 初始化表结构，含账号、限速档位、异常事件
- `images/ipsec-l2tp-gateway`：`strongSwan + accel-ppp` 网关镜像
- `images/freeradius`：RADIUS 鉴权与记账
- `images/admin-portal`：账号、会话、流量和异常事件后台

## 当前边界

- `UniConnect SSL VPN` 仅预留统一账号与配置导出接入面，本仓库不实现联软兼容 SSL 网关。
- 后台需要保存 VPN 明文密码，以便同步 `NT-Password` 到 RADIUS 并支持管理员查看连接参数；这适合小规模场景，但生产上应进一步接入专门的密钥管理。
- Docker 在当前本地环境不可用，因此本轮验证以 Python 测试和静态检查为主。
