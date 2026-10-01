# CLI2API（飞牛 fnOS 原生应用）

把 [cli2api](https://github.com/caigee-cmd/cli2api)（Qoder CLI → OpenAI 兼容 API 网关）
打包成**飞牛 fnOS 原生应用**。

- **零源码改动**：上游 Go 服务原样编译，控制台静态资源直接使用上游仓库内已提交的产物。
- **统一网关接入**：控制台走 `/app/cli2api`，复用飞牛登录态，**面板无需独立登录密码**，仅管理员可访问。
- **下游独立端口 `3010`**：标准 OpenAI SDK 直连。
- **随包携带运行时**：Qoder CLI 国内区 + 全球区组件、ripgrep 原生库、sharp/libvips 原生库全部随包，安装时不联网。

---

## 1. 功能特点

### 账号池 → 标准 API

- 标准 `/v1/chat/completions`、`/v1/models`、`/v1/messages`、`/v1/responses`
- 多账号加权轮转、失败重试、熔断与冷却
- 支持 Qoder 全球区与国内区账号，内置每日自动签到

### 官方 Web 控制台

- 账号管理、模型中心、密钥管理、运行日志、内置对话测试台
- 统一网关接入，复用飞牛登录态，**面板无需独立登录密码**，仅管理员可访问
- 控制台自带的更新入口在飞牛上不可用（没有宿主机 updater 进程），属预期降级

### 下游接入

- 独立端口 `http://<飞牛IP>:3010/v1`，任意 OpenAI SDK 直连
- 端口取上游默认值；统一网关路径仅供面板访问，外部客户端走不通
- 该端口只放行 `/v1/*` 与 `/health`，其余路径（含控制台接口 `/api/*`）一律 404

### 运行时说明

- Qoder 账号由内置 Node worker 驱动，**依赖应用中心 Node.js 运行时（`nodejs_v24`，安装时自动带上）**
- Qoder CLI 组件（国内区 + 全球区）随包携带，安装时不联网

---

## 2. 架构

```text
飞牛桌面 → CLI2API 网关（仅管理员）
                │  统一网关 /app/cli2api
                ▼
        ${TRIM_APPDEST}/cli2api.sock
                │
        fngateway（适配层，Go）
        · 剥离 /app/cli2api 前缀、改写重定向与 Cookie Path
        · 注入 x-api-key（从 qoder.db 读控制台密钥）
        · 把 X-Trim-Userid / X-Trim-Isadmin 交给面板做鉴权
        · 托管 cli2api 子进程
                │  127.0.0.1:内部端口（回环，不对外）
                ▼
        cli2api 上游二进制（零改动）
                │  QODER_NODE_BINARY / QODER_WORKER_DAEMON / ...
                ▼
        Node worker（nodejs_v24 运行时）+ Qoder CLI 组件

外部 OpenAI 客户端 ──→ 0.0.0.0:3010 ──→ 仅放行 /v1/* 与 /health
```

`fngateway` 这一层负责上游不管的事：子路径适配、免密登录（服务端注入密钥）、
管理员身份约束、端口隔离、内存约束与接入地址纠偏。上游源码零改动。

---

## 3. 安装

从应用中心（或本外部源）安装对应的 fpk：

| 架构 | 适用机型 | 包大小 |
| --- | --- | --- |
| `x86`（amd64） | x86_64 机型 | ≈ 79 MB |
| `arm`（arm64） | 飞牛 ARM 机型 | ≈ 77 MB |

`manifest` 中声明了 `install_dep_apps = nodejs_v24`，应用中心会自动带上 Node.js 运行时依赖。

命令行管理：

```bash
appcenter-cli install-fpk cli2api-0.6.13-1-amd64.fpk
appcenter-cli list
appcenter-cli start cli2api
appcenter-cli stop cli2api
```

- **升级**：数据目录（账号凭证、API 密钥、控制台密钥）全部保留；每账号运行时缓存在升级后自动清理（可重建，不影响登录状态）。
- **卸载**：向导里选择是否保留数据。选择「保留数据」后重新安装可继续使用原有账号与密钥；选择「删除全部数据」会连凭证一起清除且**无法恢复**。

---

## 4. 使用

### 4.1 控制台（管理员）

飞牛桌面 → **CLI2API 网关**。免密进入，可管理账号、模型、密钥、日志，并内置对话测试台。

### 4.2 下游接入（外部客户端）

```bash
curl http://<飞牛IP>:3010/v1/chat/completions \
  -H "Authorization: Bearer <在控制台生成的密钥>" \
  -H "Content-Type: application/json" \
  -d '{"model":"...","messages":[{"role":"user","content":"hi"}]}'
```

已支持：`/v1/chat/completions`、`/v1/models`、`/v1/messages`、`/v1/responses`、`/health`。
密钥在控制台「密钥管理」里创建；控制台自身的密钥也可以直接当 `/v1` 密钥用。

> **注意**：统一网关路径 `/app/cli2api` 仅供面板自身使用，**不要**把外部 OpenAI
> 客户端指向它 —— 它带飞牛登录态校验，且飞牛 1.2.0604+ 会拦截外部 `Authorization` 头。

### 4.3 内存占用与调优

**每个启用的 Qoder 账号 = 一个常驻 Node worker 进程**，内存随账号数线性增长。
实测（arm64 / 4GB 设备，2 个账号空闲）：

| 进程 | RSS |
| --- | --- |
| `node .../worker/src/daemon.mjs`（每账号一个） | ≈ 511 MB |
| `cli2api-linux-arm64`（上游，含账号编排） | ≈ 31 MB |
| `fngateway-linux-arm64`（网关适配层） | ≈ 11 MB |

即**两个账号 ≈ 1.0 GB 都花在 Node worker 上**，Go 侧两个进程合计仅 ~42 MB。

自 `0.6.13-1` 起，网关会给每个 worker 注入 V8 老生代上限（每个账号一份，不是总量）：

```bash
NODE_OPTIONS=--max-old-space-size=384     # 默认 384MB
```

可用环境变量覆盖（`0` = 不注入）：

| 取值 | 适用 |
| --- | --- |
| `256` | 2GB 设备 |
| `384` | 4GB 设备（默认） |
| `512` | 8GB+ 设备 |
| `0` | 关闭注入 |

```bash
QODER_WORKER_MAX_OLD_SPACE_MB=256
```

生效值会写进 `${TRIM_PKGVAR}/panel.log`（`Worker 堆上限:` 一行）。

> **别指望它把 511MB 的基线压下去。** 空闲 RSS 511MB 远低于 Node 在 4GB 设备上的
> 默认堆上限，说明占用大头是 WASM 实例与 bundle 编译产物，不计入
> `--max-old-space-size`。该上限的作用是**兜底**：防止 JS 堆侧随时间无界增长。
> 设得过小会让 worker OOM 退出并被反复重启（日志里出现
> `JavaScript heap out of memory`），此时上调该值。

**真正能按比例省内存的只有一条：减少同时启用的账号数。** 在控制台禁用不常用的
账号会直接停掉对应 worker，内存即时归还（每个省 ~511MB）。

### 4.4 数据与日志位置

| 内容 | 路径 |
| --- | --- |
| 数据目录（`qoder.db`：账号凭证 / 密钥） | `${TRIM_PKGVAR}`，即 `/vol*/@appdata/cli2api` |
| 生命周期日志（启停） | `${TRIM_PKGVAR}/main.log` |
| 网关日志（面板侧，含子进程起停） | `${TRIM_PKGVAR}/panel.log` |
| 上游日志（cli2api 自身输出） | `${TRIM_PKGVAR}/cli2api.log` |
| 网关 PID | `${TRIM_PKGVAR}/fngateway.pid` |
| 网关 socket | `${TRIM_APPDEST}/cli2api.sock` |

`panel.log` / `cli2api.log` 单文件超过 8MB 会自动轮转为 `.1`。
排查账号起不来时先看 `cli2api.log`。

---

## 5. 权限与安全设计

| 项 | 取值 | 说明 |
| --- | --- | --- |
| 运行身份 | `run-as=package`（用户 `cli2api`） | 非 root；不加入任何特权组 |
| fnOS 系统资源 | 无（`config/resource` 为空） | 不申请文件共享、Docker、GPU 等能力 |
| 控制台可见性 | `allUsers=false` + `accessPerm=readonly` | 仅管理员 |
| 控制台密钥 | 存 `qoder.db`，由网关服务端读取注入 | 前端只有占位串，密钥不进浏览器、不进日志 |
| 开放 API Token | 未使用 | 本应用不调用 `/api/v1/trimapp`，无 `TRIM_API_TOKEN` 参与 |
| 下游端口 | `3010`，仅 `/v1/*` + `/health` | 其余路径一律拒绝，避免控制台从外部裸奔 |
| 身份判定 | 取网关注入的 `X-Trim-Isadmin` | 不信任请求体 / 查询参数中的身份标记 |

---

## 6. 上游与许可

上游仓库：[`caigee-cmd/cli2api`](https://github.com/caigee-cmd/cli2api)，当前锁定 **v0.6.13**。

随包组件的许可随包附带（见打包产物中的 `UPSTREAM.txt` 与 `LICENSE.upstream`）：

- cli2api / fngateway：MIT
- Qoder CLI 组件（`@qoder-ai/qodercli`、`@qodercn-ai/qoderclicn`）：Apache-2.0
- sharp / libvips：Apache-2.0 / LGPL-3.0

> 本应用仅用于私有环境下的个人账号管理，需自备已获授权的 Qoder 账号，请遵守上游服务条款。

- 打包仓库：<https://github.com/sushazhi/fnos-cli2api>
- 问题反馈：<https://github.com/sushazhi/fnos-cli2api/issues>
