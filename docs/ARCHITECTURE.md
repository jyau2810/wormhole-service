# 技术文档

## 系统目标

该项目面向小规模远程接入账号分发场景，目标是用一套相对简单、可自托管、便于运维的组件组合，完成以下能力：

- 原生 `L2TP/IPSec PSK` 接入
- 账号鉴权、过期控制和并发控制
- 带宽档位下发
- 会话、流量、认证失败和异常事件可观测
- 为未来接入外部 `UniConnect SSL VPN` 保留统一账号源

## 架构总览

核心链路如下：

1. 用户端通过 `L2TP/IPSec PSK` 连接 `ipsec-l2tp-gateway`
2. 网关把账号鉴权和记账请求发送到 `FreeRADIUS`
3. `FreeRADIUS` 从 `MariaDB` 读取账号策略并回传控制属性
4. `admin-portal` 管理账号、展示接入配置，并读取审计与异常数据

组件职责：

- `ipsec-l2tp-gateway`
  - `strongSwan` 负责 `IPSec PSK`
  - `accel-ppp` 负责 `L2TP/PPP`、RADIUS 鉴权和记账
- `freeradius`
  - 统一认证入口
  - 根据数据库字段判断是否允许接入
  - 返回并发限制和限速属性
- `db`
  - 存储账号、限速档位、认证日志、会话和异常事件
- `admin-portal`
  - 提供管理界面
  - 汇总可观测性数据
  - 导出客户端接入参数

## 技术选型

### 为什么选 `L2TP/IPSec PSK`

- 客户端覆盖面高，适合 `macOS / Windows / iPhone / Android 12 以下`
- 不依赖自研客户端，适合小规模场景快速落地
- 与 `RADIUS` 组合成熟，便于接入统一账号体系

当前边界：

- `Android 12+` 对原生 `L2TP/IPSec` 支持受限
- 本仓库不实现 `UniConnect SSL VPN` 兼容网关，只保留账号与配置对接面

### 为什么选 `strongSwan + accel-ppp`

- `strongSwan` 负责 `IPSec` 能力，生态成熟
- `accel-ppp` 对 `L2TP/PPP` 和 `RADIUS` 协作支持直接，适合这类轻量接入网关
- 两者组合便于把“隧道建立”和“账号策略控制”拆开处理

### 为什么选 `FreeRADIUS`

- 与 `PPP/L2TP` 接入链路天然匹配
- 可直接使用 `NT-Password`、`Expiration`、`Simultaneous-Use` 等属性
- 同时覆盖鉴权、回复属性和记账数据入口，减少额外控制面逻辑

### 为什么选 `MariaDB`

- 结构化存储适合账号、档位、会话、日志和事件模型
- 易于与 `FreeRADIUS` 和后台服务共享
- 部署和维护成本较低，适合小规模单机或轻量部署

### 为什么保留后台而不是只用数据库

- 需要统一展示共享密钥、接入点和用户侧配置
- 需要给运营或管理员提供非 SQL 的日常操作入口
- 需要汇总认证失败、活跃会话、流量和异常事件

## 认证与策略模型

每次登录依赖两层参数：

1. 网关级共享密钥 `VPN_SHARED_PSK`
2. 账号级用户名与密码

RADIUS 中的关键控制属性：

- `NT-Password`
- `Expiration`
- `Simultaneous-Use`

回传给网关的常用回复属性：

- `Filter-Id`
- `WISPr-Bandwidth-Max-Up`
- `WISPr-Bandwidth-Max-Down`

每个账号具备的核心策略：

- 启用或禁用状态
- 到期时间
- 限速档位
- 最大并发会话数

## 可观测性设计

后台聚合以下数据：

- `radpostauth`：最近认证成功与失败
- `radacct`：活动会话与累计流量
- `vpn_account_events`：异常事件

当前内置异常规则：

- 并发会话数超限
- `15` 分钟内失败认证过多
- `30` 分钟内跨多个网关反复建立会话
- `5` 分钟流量超过限速档位预估阈值

## 运维边界

当前设计有意保持简单，因此也带来明确边界：

- 后台需要保存 VPN 明文密码，以便同步 `NT-Password` 并向管理员展示连接参数
- 更适合小规模部署，不以多租户、大规模横向扩展为目标
- 生产环境如对密钥管理要求更高，应接入独立机密管理系统
- 本仓库不维护设备证书、设备槽位或完整 `CA/CRL` 生命周期
