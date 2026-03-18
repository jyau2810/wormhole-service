---
name: wormhole-log-triage
description: 在 wormhole-service 项目中按故障类型定位应收集的日志、状态和数据库记录，并基于日志做分层排障分析。适用于后台异常、账号到期/续期问题、证书签发失败、RADIUS 认证失败、VPN 无法连接、连接后无流量等场景。
---

# Wormhole Log Triage

## Use When
- 用户反馈“报错”“故障”“连不上”“续期没生效”“账号不可用”“证书下载失败”“后台 500”“服务启动失败”
- 需要先告诉用户从哪里拿日志，再根据日志判断根因
- 需要在本项目的 `admin-portal -> ca-api -> MariaDB/radcheck -> FreeRADIUS -> ocserv` 调用链上做排障

## First Response
先判断故障落点，再明确要求用户提供最小必要日志。优先使用文件日志，只有文件日志不足时再补 `docker compose logs`。

默认先确认三件事：
1. 故障时间窗口，精确到分钟
2. 发生环境
   - 本机非 VPN 联调
   - 服务器生产环境
3. 故障现象
   - 后台打不开或接口报错
   - 账号创建/续期/禁用未生效
   - 用户名密码认证失败
   - 证书签发/下载/吊销失败
   - VPN 连不上
   - VPN 已连接但无流量或无法上网

## Log Map

### 后台打不开、接口 4xx/5xx、管理操作报错
先拿：
- `var/log/admin-portal/error.log`
- `var/log/admin-portal/access.log`
- `var/log/admin-portal/app.log`
- `var/log/mariadb/error.log`

需要时补：
- `docker compose logs --tail=200 admin-portal`

分析重点：
- 用 `request_id` 关联 `access.log` 和 `error.log`
- 看接口路径、状态码、耗时、未捕获异常
- 如果是创建账号、续期、禁用、改密失败，再继续检查 `radcheck` 是否被正确写入

### 账号创建成功但续期/禁用/改密未生效
先拿：
- `var/log/admin-portal/app.log`
- `var/log/mariadb/error.log`
- `var/log/freeradius/freeradius.log`

同时检查数据库：
```sql
SELECT username, attribute, op, value
FROM radcheck
WHERE username = '<username>'
ORDER BY attribute;
```

分析重点：
- `Crypt-Password` 是否存在
- `Expiration` 是否存在且格式正确
- 操作时间后 FreeRADIUS 是否仍读取到旧数据
- 如果是认证已发生，再查 `radpostauth`

### 用户名密码认证失败、到期后仍能登录、续期后仍不能登录
先拿：
- `var/log/freeradius/freeradius.log`
- `var/log/admin-portal/app.log`

同时检查数据库：
```sql
SELECT username, reply, authdate
FROM radpostauth
WHERE username = '<username>'
ORDER BY authdate DESC
LIMIT 20;
```

```sql
SELECT username, attribute, op, value
FROM radcheck
WHERE username = '<username>'
ORDER BY attribute;
```

分析重点：
- FreeRADIUS 拒绝原因是密码错误、账号过期还是属性缺失
- `Expiration` 是否已按预期更新
- 如果后台显示正常但认证失败，优先怀疑 `radcheck` 写入、时间格式、时区或密码同步问题

### 证书签发、下载、吊销失败
先拿：
- `var/log/ca-api/error.log`
- `var/log/ca-api/access.log`
- `var/log/ca-api/app.log`
- `var/log/admin-portal/app.log`

需要时补：
- `docker compose logs --tail=200 ca-api`

分析重点：
- 先看 CA API 是否成功收到请求
- 再看是签发失败、文件打包失败、CRL 更新失败还是下载链路异常
- 若问题出现在设备签发数量限制，继续检查后台账户下设备槽位状态

### VPN 连不上、连接时立即断开
先拿：
- `var/log/ocserv/error.log`
- `var/log/ocserv/ocserv.log`
- `var/log/freeradius/freeradius.log`

需要时补：
- `docker compose logs --tail=200 ocserv`
- `docker compose logs --tail=200 freeradius`

分析重点：
- ocserv 是否启动正常，证书和监听端口是否就绪
- 认证阶段失败还是隧道建立阶段失败
- 是否有证书吊销、账号过期、RADIUS 拒绝、TUN 或权限问题

### VPN 已连接但无流量、无法访问公网、DNS 异常
先拿：
- `var/log/ocserv/ocserv.log`
- `var/log/ocserv/error.log`

需要时补运行状态：
```bash
docker compose exec ocserv occtl show users
docker compose exec ocserv iptables -t nat -S
docker compose exec ocserv iptables -S FORWARD
```

分析重点：
- 是否已建立会话
- NAT 和 FORWARD 规则是否存在
- 更偏宿主机网络、转发、云防火墙或 DNS 下发问题，不要只盯应用日志

### 容器启动失败、服务健康检查不通过
先拿：
- `docker compose ps`
- `docker compose logs --tail=200 <service>`

同时看文件日志：
- `var/log/admin-portal/error.log`
- `var/log/ca-api/error.log`
- `var/log/freeradius/freeradius.log`
- `var/log/ocserv/error.log`
- `var/log/mariadb/error.log`

分析重点：
- 区分镜像构建失败、配置渲染失败、数据库未就绪、证书缺失、权限不足

## Analysis Workflow
拿到日志后，按下面顺序分析，不要跳步：

1. 定位时间线
   - 用故障发生时间、用户名、设备名、接口路径缩小时间窗口
2. 定位入口服务
   - 后台操作先看 `admin-portal`
   - 证书问题先看 `ca-api`
   - 用户认证问题先看 `freeradius`
   - VPN 会话问题先看 `ocserv`
3. 做跨服务关联
   - `request_id` 关联 Python 服务请求
   - `username` 关联 `radcheck`、`radpostauth`、`radacct`
   - 用同一时间窗口串联后台操作和认证结果
4. 判断根因层级
   - 配置错误
   - 数据未写入或写错
   - 服务内部异常
   - 外部依赖异常
   - 宿主机网络/NAT/权限问题
5. 给出结论和下一步
   - 先给最可能根因
   - 再给验证命令
   - 最后给修复建议

## Response Template
排障回复优先按这个结构输出：

1. 先拿哪些日志
   - 直接列文件路径和必要命令
2. 已看到的关键现象
   - 只摘高信号错误，不堆原始日志
3. 判断
   - 最可能根因
   - 次可能根因
4. 下一步验证
   - 1 到 3 条最短路径命令
5. 修复建议
   - 只写与当前根因直接相关的动作

## Project-Specific Paths
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

## Local vs Server
- 本机联调只覆盖 `db + ca-api + freeradius + admin-portal + logrotate`
- 本机没有 VPN 数据面，不要让用户在本机查 `ocserv` 的 TUN、NAT、转发行为
- 服务器生产环境遇到 VPN 连通性问题，必须把 `ocserv` 和宿主机网络状态一起纳入分析
