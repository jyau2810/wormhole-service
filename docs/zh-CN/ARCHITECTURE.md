# 架构说明

英文原版请见 [ARCHITECTURE.md](/Users/jyau/Documents/Projects/wormhole-service/docs/ARCHITECTURE.md)。

## 总览

当前实现是一个面向小规模场景的双栈接入控制平面：

- `ipsec-l2tp-gateway`
  - `strongSwan` 处理 `IPSec PSK`
  - `accel-ppp` 处理 `L2TP/PPP`、RADIUS 鉴权与记账
- `FreeRADIUS` 负责账号鉴权、到期控制与回传限速属性
- `MariaDB` 存储账号、限速档位、认证日志、会话和异常事件
- `admin-portal` 负责账号管理、接入点展示、流量观察和人工处置

## 认证模型

每次原生客户端登录依赖两层参数：

1. 网关级共享密钥 `VPN_SHARED_PSK`
2. 账号级用户名/密码

RADIUS 中同步的核心属性：

- `NT-Password`
- `Expiration`
- `Simultaneous-Use`

回传给网关的回复属性：

- `Filter-Id`
- `WISPr-Bandwidth-Max-Up`
- `WISPr-Bandwidth-Max-Down`

## 账号与策略

每个账号具备：

- 启用/禁用状态
- 到期时间
- 限速档位
- 最大并发会话数

后台不再维护设备证书、设备槽位或 CA/CRL 生命周期。

## 可观测性

后台聚合以下数据：

- `radpostauth` 中最近认证成功/失败
- `radacct` 中活动会话和累计流量
- `vpn_account_events` 中异常事件

当前内置异常规则：

- 并发会话数超限
- 15 分钟内失败认证过多
- 30 分钟内跨多个网关反复建立会话
- 5 分钟流量超过限速档位预估阈值

## UniConnect 预留

Android 12+ 的 `UniConnect SSL VPN` 在本仓库中仅预留：

- 统一账号源
- 网关元数据导出
- 限速与异常事件模型

联软兼容 SSL 网关本身不在当前仓库实现范围内。
