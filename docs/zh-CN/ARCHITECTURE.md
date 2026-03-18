# 架构说明

英文原版请见 [ARCHITECTURE.md](/Users/yaoji/Documents/Workspace/wormhole-service/docs/ARCHITECTURE.md)。

## 总览

这套方案面向单机 Docker 部署，职责划分如下：

- `ocserv` 在 `443/tcp` 和 `443/udp` 终止 VPN 流量
- `FreeRADIUS` 校验账号密码和账号有效期
- `MariaDB` 存储 VPN 账号、设备槽位、RADIUS 校验项、认证日志和记账数据
- `ca-api` 管理内部 CA、客户端证书签发、吊销和 CRL 生成
- `admin-portal` 提供日常运维后台

## 认证模型

每次 VPN 登录都要求两个独立因素：

1. 由内部 CA 签发且仍有效的客户端证书
2. 由 FreeRADIUS 校验通过的 VPN 用户名和密码

在 `ocserv` 中通过以下方式实现：

- `auth = "certificate"`
- `auth = "radius[...]"`

账号有效期通过写入 `radcheck` 中的以下属性来控制：

- `Crypt-Password`
- `Expiration`

当账号被禁用时，后台会把有效的 RADIUS 到期时间直接改写为当前 UTC 时间，从而立即阻止新登录。

## 设备绑定模型

设备绑定由应用层控制，不做硬件指纹绑定。

- 每个账号最多拥有 `2` 个有效设备槽位
- 每个设备槽位对应 1 张有效客户端证书
- 吊销设备证书后会释放对应槽位
- 试图签发第 3 张设备证书时，后台会直接拒绝

数据真实来源是 `vpn_devices` 表。

## 日志与可观测性

- `radpostauth` 记录成功和失败的认证结果
- `radacct` 记录活动和历史会话，前提是 NAS 发送 accounting 包
- 后台页面展示：
  - 账号到期时间
  - 已占用设备数
  - 最近认证记录
  - 来自 `radacct` 的当前在线会话
- 文件日志写入宿主机 `var/log/`，并由 `logrotate` sidecar 每日滚动

## 证书布局

`ca-data` 卷由 `ca-api` 和 `ocserv` 共享。

- `/data/ca/ca-cert.pem`
- `/data/ca/ca-key.pem`
- `/data/ca/crl.pem`
- `/data/server/server-cert.pem`
- `/data/server/server-key.pem`
- `/data/clients/<serial>/...`

`ocserv` 以只读方式把同一卷挂载到 `/srv/pki`。

## 已知边界

- 首次部署使用内部 CA 生成的 VPN 服务端证书；有域名后应替换为公网证书
- 设备“最后在线时间”目前来自 RADIUS 认证和记账历史推断，不是独立的设备心跳
- 本方案面向小规模场景，不是多节点高可用部署方案
