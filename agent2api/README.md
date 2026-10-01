# Agent2API（飞牛 fnOS 原生应用）

把**多提供商账号池**变成标准 **OpenAI 兼容 API** 的飞牛原生应用。

上游 [aimod-cc/agent2api](https://github.com/aimod-cc/agent2api) 原样集成（零源码改动），
外套一层飞牛网关适配层 `fngateway`。上游是 Rust 单文件静态二进制，自带官方 Web
控制台，内置 7 个提供商适配，把客户端登录态复用成标准 OpenAI 接口。

- **单文件静态二进制**：不依赖 Docker，**不依赖 Node.js 运行时**，SQLite 静态链接，安装即用。
- **统一网关接入**：控制台走 `/app/agent2api`，复用飞牛登录态，**面板无需独立登录密码**，仅管理员可访问。
- **下游独立端口 `3065`**：标准 OpenAI 兼容接口，任意 OpenAI SDK 直连。
- **账号凭据明文存储**：上游既有设计，请勿在多人共享的设备上使用。

---

## 1. 功能特点

### 统一网关接入 & fnOS 集成

- 通过 fnOS 统一网关访问控制台，无需独立端口、无需额外账号
- 网关自动校验登录态，免密登录；控制台仅管理员可见可访问
- 网关密钥由后端生成并注入，**密钥不下发到浏览器**
- 支持 fnOS V1.2.0401 及以上版本

### 账号池 → 标准 API

- 标准 `/v1/chat/completions`、`/v1/models`、`/v1/responses`
- 多账号轮转、失败重试，本地 SQLite 持久化
- 内置 7 个提供商适配：**WorkBuddy、小浣熊（Raccoon）、CatPaw、AutoClaw、Qoder、Cline Free、Cline Pass**
- 其中 WorkBuddy / Qoder / Cline 为设备码轮询登录，只有浏览器时最省事；
  AutoClaw / CatPaw 走 loopback 回调（要求浏览器与网关同机）；
  小浣熊用自定义 scheme `office-raccoon://` 回调，只能靠粘贴凭据

### 官方 Web 控制台

- 账号管理（扫码 / 设备码登录上游客户端）、模型中心、API 密钥
- 运行日志与请求记录、定时任务、对话测试台
- 控制台自带的「检查更新」在飞牛上不可用（没有宿主机 updater 进程），
  属预期降级 —— 升级请用应用中心

---

## 2. 两条入口

一个应用，两条入口，互不干扰：

| 入口 | 路径 / 端口 | 给谁用 | 鉴权 |
| --- | --- | --- | --- |
| 统一网关 | `/app/agent2api` | 飞牛桌面里的 Web 控制台 | 飞牛登录态 + 仅管理员 |
| 下游端口 | `http://<飞牛IP>:3065/v1` | 任意 OpenAI 兼容客户端 | `Authorization: Bearer <网关密钥>` |

> **为什么不把外部客户端指到 `/app/agent2api`？** 飞牛 1.2.0604+ 会拦截非飞牛
> 票据的 `Authorization` 头，外部客户端的 `Bearer` 会被吃掉。统一网关那条路径
> 只给桌面面板用。

架构：

```text
浏览器 ──https──> 飞牛统一网关 ──unix socket──> fngateway ──tcp 127.0.0.1:<随机>──> agent2api-server
（仅管理员）        /app/agent2api            （适配层）     （内核分配）              （上游二进制）

OpenAI SDK ──http──> http://<飞牛IP>:3065/v1 ─────────────────────────────────────> agent2api-server
（任意客户端）        （独立下游端口，不经统一网关）
```

`fngateway` 这一层负责上游不管的事：持有 Unix socket、注入网关密钥、
改写控制台子路径与 Cookie Path、轮转日志与优雅停机。上游源码零改动。

---

## 3. 安装

从应用中心（或本外部源）安装对应的 fpk：

| 架构 | 适用机型 | 包大小 |
| --- | --- | --- |
| `x86`（amd64） | x86_64 机型 | ≈ 8.5 MB |
| `arm`（arm64） | 飞牛 ARM 机型 | ≈ 8.0 MB |

- **升级**：数据（`data/agent2api.db`）与网关密钥（`apikey`）都会保留，升级脚本幂等，不会重建账号数据。
- **卸载**：向导里有「保留数据」选项，默认**保留**数据。

---

## 4. 使用

### 4.1 控制台（管理员）

飞牛桌面点应用图标，走统一网关 `/app/agent2api`，**仅管理员可见可访问**。
面板**不需要单独登录** —— 网关密钥由后端注入，浏览器侧只拿到一个占位值。

面板里可以：加账号（扫码 / 设备码登录上游客户端）、管模型、发 API 密钥、
看运行日志与请求记录、定时任务、对话测试台。

### 4.2 下游接入（外部客户端）

标准 OpenAI 兼容接口在**独立端口**：

```text
http://<飞牛IP>:3065/v1
```

网关密钥在 `${TRIM_PKGVAR}/apikey`（root / 应用属主可读）：

```bash
cat /var/apps/agent2api/var/apikey
```

客户端配置（以 OpenAI SDK 为例）：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://192.168.0.2:3065/v1",
    api_key="<apikey 内容>",
)
```

### 4.3 数据与日志位置

全部在 `${TRIM_PKGVAR}`（即 `/var/apps/agent2api/var/`）：

| 路径 | 内容 |
| --- | --- |
| `data/agent2api.db` | 账号、日志、请求统计、调试报文、脱敏词表、网关配置（SQLite） |
| `data/agent2api.db-wal` / `-shm` | WAL 附属文件，**备份时要一起拷** |
| `apikey` | 网关密钥（0600，首次启动自动生成） |
| `home/` | 子进程的 `HOME`（0700） |
| `panel.log` | `fngateway` 自己的日志（8 MB 轮转） |
| `agent2api.log` | 上游子进程的 stdout/stderr（8 MB 轮转） |
| `main.log` | 飞牛生命周期脚本日志 |

命令行管理（`TRIM_*` 由飞牛注入，需在应用上下文里执行）：

```bash
./cmd/main start | stop | status      # status: 0=运行中 3=未运行 1=参数错
```

---

## 5. 权限与安全设计

- **最小权限**：以 `agent2api` 用户/组运行（`run-as=package`），不用 root。
- **网关密钥只走服务端**：`fngateway` 生成 → 环境变量传子进程 → 面板里只显示掩码，
  密钥从不下发给浏览器。
- **无面板登录 = 无 Cookie**：面板登录闸门不启用，全程不下发 `Set-Cookie`；
  即便将来启用，`fngateway` 也已把 Cookie 的 `Path` 收窄到应用子路径。
- **socket 权限最小化**：socket 建在 `${TRIM_APPDEST}`，启动前与停止时都清理残留。
- **下游端口绑定所有网卡**：`agent2api-server` 监听 `0.0.0.0:3065`（只绑回环会让
  局域网客户端连不上）；子进程内部用的回环端口由内核分配、不对外暴露。
- **路径安全**：卸载脚本先确认 `DATA_DIR != "/"` 才递归删除。

> ⚠️ **凭据明文**：上游把 accessToken / refreshToken 以**明文**存在
> `data/agent2api.db`。这是上游的既有设计，本适配层没有改变它。
> 不要在多人共享的设备上使用，也不要提交 / 分享该文件。

---

## 6. 上游与许可

本适配层（`fngateway/`、`cmd/`、`config/`、`wizard/`、`manifest`、`build.py`、
图标与桌面入口）以 **MIT** 发布。

上游 agent2api 有**自己的许可**，随包提交在 fpk 内的 `LICENSE.upstream`：
MIT 条款正文**外加**一份「使用声明」，其中第 3 条禁止商业用途与二次分发牟利
（个人学习、研究、自用，以及不以牟利为目的的分享与交流不受此限）。
完整授权 = MIT 条款 + 使用声明，两者冲突时以更严格的一方为准。

- 上游：<https://github.com/aimod-cc/agent2api>（`Copyright (c) 2026 aimod-cc`）
- 打包仓库：<https://github.com/sushazhi/fnos-agent2api>
- 问题反馈：<https://github.com/sushazhi/fnos-agent2api/issues>
