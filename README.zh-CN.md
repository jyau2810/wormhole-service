# Wormhole VPN Stack

中文文档入口。英文原版请见 [README.md](/Users/yaoji/Documents/Workspace/wormhole-service/README.md)。

这是一个面向小规模账号分发场景的 Docker 化 VPN 方案，包含：

- OpenConnect/ocserv VPN
- 基于 FreeRADIUS 的用户名密码认证
- 按账号控制有效期
- 每个账号最多绑定 2 台设备证书
- 内部 CA 与 CRL 管理
- 轻量管理后台

## 快速开始

1. 复制 `.env.example` 为 `.env`，并填入强密码和密钥。
2. 阅读 `docs/zh-CN/DEPLOY.md`，完成宿主机前置条件。
3. 启动整套服务：

```bash
docker compose --env-file .env up -d --build
```

4. 在服务器本机或通过 SSH 隧道访问管理后台 `http://127.0.0.1:${ADMIN_PORTAL_PORT}`。

## 本机非 VPN 联调

在 macOS 上，只建议联调非 VPN 数据面服务。

```bash
cp .env.example .env
make local-up
make local-smoke
```

详见 `docs/zh-CN/LOCAL_DEV.md`。

## 文档索引

- 英文：
  - `README.md`
  - `env.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DEPLOY.md`
  - `docs/LOCAL_DEV.md`
  - `docs/OPERATIONS.md`
  - `docs/TROUBLESHOOTING.md`
- 中文：
  - `README.zh-CN.md`
  - `env.zh-CN.md`
  - `docs/zh-CN/ARCHITECTURE.md`
  - `docs/zh-CN/DEPLOY.md`
  - `docs/zh-CN/LOCAL_DEV.md`
  - `docs/zh-CN/OPERATIONS.md`
  - `docs/zh-CN/TROUBLESHOOTING.md`

## 交付内容

- `docker-compose.yml`：单命令部署入口
- `Makefile`：本机联调和 smoke test 辅助命令
- `.env.example`：环境变量样例
- `env.md` / `env.zh-CN.md`：环境变量说明
- `bootstrap/db`：MariaDB 初始化表结构
- `images/ocserv`：VPN 服务镜像与运行模板
- `images/freeradius`：FreeRADIUS 镜像与 SQL 配置
- `images/ca-api`：内部 CA/CRL API
- `images/admin-portal`：管理后台
- `docs/`：架构、部署、运维、排障文档
- `var/log/`：宿主机侧日志目录

## 说明

- 首次部署会由内部 CA 生成自签名 VPN 服务端证书。
- 进入生产前，建议在有域名后替换为公网证书。
- 当前本地环境没有 Docker，因此本仓库的验证仍以静态检查和 Python 测试为主。
