# FnDepot — 飞牛 fnOS 第三方应用源

一个可直接在飞牛 fnOS 客户端里添加的**外部应用源**，收录一批以「原生应用」形态
打包的飞牛三方应用（`.fpk`）。所有应用都由本人（yukihana）适配与维护，安装即用。

- **源地址**：`https://github.com/sushazhi/FnDepot`
- **索引文件**：本仓库根目录的 [`fnpack.json`](./fnpack.json)（外部源规范 V2）
- **应用总数**：7 个（5 个影音/系统工具 + 2 个 AI API 网关）

> 外部源由用户自行添加，仅在用户本地客户端中生效。FnDepot 不对外部源的应用代码、
> 安装包安全性或运行稳定性做审核、担保或背书。添加方式与源规范见
> [《外部应用源 V2 编写说明》](./docs/README.fnpack-v2-spec.md)。

---

## 1. 应用一览

> 下表的「最新版本」列由同步脚本自动刷新，**请勿手工编辑**（改了下一次同步也会被覆盖）。

| 应用 | 说明 | 分类 | 架构 | 最新版本 |
| --- | --- | --- | --- | --- |
| [飞牛日志管理](#21-飞牛日志管理logmanager) | 集中管理三方应用散落的日志文件 | 系统工具 | `all` | 0.8.1 |
| [qBittorrent](#22-qbittorrent) | 功能强大的 BitTorrent 下载工具 | 影音娱乐 | `x86` / `arm` | 5.2.3.2 |
| [Transmission](#23-transmission) | 轻量级 BitTorrent 下载工具 | 影音娱乐 | `x86` / `arm` | 4.1.3.4 |
| [MoviePilot](#24-moviepilot) | NAS 媒体库自动化管理 | 影音娱乐 | `x86` / `arm` | 1.0.7 |
| [Agent2API](#25-agent2api) | 多提供商账号池 → OpenAI 兼容 API | AI赋能 / 编程开发 | `x86` / `arm` | 2.9.0-2 |
| [CLI2API](#26-cli2api) | Qoder CLI → OpenAI 兼容 API | AI赋能 / 编程开发 | `x86` / `arm` | 0.6.13-1 |
| [Mihomo](#27-mihomo) | Clash.Meta 代理内核，带控制面板 | 系统工具 | `x86` / `arm` | 1.0.6 |

---

## 2. 应用介绍

### 2.1 飞牛日志管理（logmanager）

> 把散落在各个目录里的飞牛三方应用日志，集中到一个界面里看。

飞牛三方应用的日志分散在存储空间应用目录、`/var/log/apps/`、Docker 容器等多个
位置，排查问题时要来回切换。本应用把这些日志目录统一收拢，提供多标签页查看、
实时追踪、搜索过滤、导出与自动清理。

- **统一网关接入**：通过 fnOS 统一网关访问，无需独立端口，网关自动校验登录态、免密登录
- **原生 WebSocket**：日志流与通知推送走原生 WS，替代 HTTP 轮询
- **多标签页**：同时打开多个日志文件，非阻塞切换，重复打开自动激活已有标签
- **日志查看与追踪**：流式读取大文件、倒序查看、关键词/正则高亮、类似 `tail -f` 的实时追踪
- **日志导出**：TXT / JSON / CSV 多格式，支持 Docker 容器日志
- **日志管理**：清空大文件、批量清理旧归档、清理已卸载应用残留目录（移入回收站，可还原）
- **Docker 容器日志**、**Linux 内核版本管理**、**进程管理**（进程列表、打开的文件、进程日志）
- **通知推送**：22 种通知渠道，支持 IP 白名单规则
- **MCP 服务器**：支持 AI Agent 接入管理日志
- **多语言与主题**：集成 fnOS JS SDK（`@trimjs/web-app`），跟随系统主题与语言

- 运行身份：`root`（需要读取各应用日志目录）
- 最低系统版本：fnOS 1.2.0401
- 详细说明：[`logmanager/README.md`](./logmanager/README.md)

### 2.2 qBittorrent

> 功能强大的 BitTorrent 下载工具，带 AI 客户端可直接管理的 MCP Server。

- **完整下载能力**：RSS 订阅、搜索引擎、速度控制、WebUI 远程访问
- **双 WebUI 智能适配**：自动识别并适配 VueTorrent 与原生 WebUI
- **MCP Server 内置**：AI 客户端可通过 MCP 协议直接管理下载任务；标题栏提供开关、端口、API Key 复制与重新生成
- **安全默认**：删除/停止/开始任务等高危操作默认禁用，可在面板开启
- **API 透传**：完整接入 qBittorrent WebUI API；WebUI 监听 `0.0.0.0`，支持局域网直连
- **自动检测更新**

- 运行身份：`package`
- 最低系统版本：fnOS 1.1.3104
- 详细说明：[`qbittorrent/README.md`](./qbittorrent/README.md)

### 2.3 Transmission

> 轻量级 BitTorrent 下载工具，默认启用现代简洁的 Transmission Web 界面。

- **标准 BitTorrent 能力**：磁力链接、种子文件、DHT / PEX / LSD P2P 网络
- **现代 Web 界面**：默认启用简洁版 Web UI，接入 fnOS 统一网关免密登录
- **全静态编译**：`transmission-daemon` 改为 Alpine musl 全静态编译，去除 glibc 动态库依赖
- **自动检测更新**

- 运行身份：`package`
- 最低系统版本：fnOS 1.1.3105
- 详细说明：[`transmission/README.md`](./transmission/README.md)

### 2.4 MoviePilot

> NAS 媒体库自动化管理，不依赖 Docker 的原生应用。

- **自动化流程**：订阅、搜索、下载、媒体整理与刮削、媒体库刷新、消息通知
- **不依赖 Docker**：自带 Python 运行时的原生应用，通过 fnOS 统一网关免密访问
- **开箱即用**：默认使用 SQLite，无需额外部署数据库
- **上游同步**：跟随上游 MoviePilot 版本更新

- 运行身份：`package`
- 最低系统版本：fnOS 1.1.3104
- 详细说明：[`moviepilot/README.md`](./moviepilot/README.md)

### 2.5 Agent2API

> 把多提供商账号池变成标准 OpenAI 兼容 API。单文件静态二进制，不依赖 Docker、
> 不依赖 Node 运行时。

上游 [aimod-cc/agent2api](https://github.com/aimod-cc/agent2api) 原样集成（零源码
改动），外套一层飞牛网关适配层。

- **7 个提供商适配**：WorkBuddy、小浣熊（Raccoon）、CatPaw、AutoClaw、Qoder、Cline Free、Cline Pass
- **标准接口**：`/v1/chat/completions`、`/v1/models`、`/v1/responses`
- **账号池调度**：多账号轮转、失败重试，本地 SQLite 持久化
- **官方控制台**：账号管理、模型中心、API 密钥、运行日志、请求记录、定时任务、对话测试台
- **统一网关接入**：控制台走 `/app/agent2api`，免密登录，仅管理员可访问
- **下游独立端口 `3065`**：任意 OpenAI SDK 直连

- 运行身份：`package`
- 最低系统版本：fnOS 1.2.0401
- ⚠️ 账号凭据按上游设计以**明文**存储，请勿在多人共享的设备上使用
- 详细说明：[`agent2api/README.md`](./agent2api/README.md)

### 2.6 CLI2API

> 把 Qoder CLI 变成标准 OpenAI 兼容 API，Qoder 运行组件随包携带、安装即用。

上游 [caigee-cmd/cli2api](https://github.com/caigee-cmd/cli2api) 原样编译（零源码
改动），控制台静态资源直接使用上游已提交的产物。

- **标准接口**：`/v1/chat/completions`、`/v1/models`、`/v1/messages`、`/v1/responses`
- **账号池调度**：多账号加权轮转、失败重试、熔断与冷却，支持 Qoder 全球区与国内区账号
- **官方控制台**：账号管理、模型中心、密钥管理、运行日志、内置对话测试台
- **统一网关接入**：控制台走 `/app/cli2api`，免密登录，仅管理员可访问
- **下游独立端口 `3010`**：任意 OpenAI SDK 直连
- **随包运行时**：Qoder CLI（国内区 + 全球区）组件、ripgrep、sharp/libvips 原生库全部随包，安装时不联网
- **内存可控**：每个启用的账号是一个常驻 Node worker（≈511 MB），网关为每个 worker 注入 V8 堆上限（默认 384 MB，可用 `QODER_WORKER_MAX_OLD_SPACE_MB` 调整）

- 运行身份：`package`；依赖应用中心 Node.js 运行时 `nodejs_v24`
- 最低系统版本：fnOS 1.2.0401
- 详细说明：[`cli2api/README.md`](./cli2api/README.md)

### 2.7 Mihomo

> 把 mihomo（Clash.Meta）代理内核做成飞牛原生应用，不带 Docker。

上游 [MetaCubeX/mihomo](https://github.com/MetaCubeX/mihomo) 内核 + 配套适配与打包层。

- **混合代理端口**（默认 `7890`）：HTTP / SOCKS5 同端口，局域网设备与容器直接可用
- **Clash API**（默认 `9090`）：供 MetaCubeXD、Zashboard 等第三方面板与客户端连接
- **内置控制面板**：首次点图标可选 **MetaCubeXD**（官方面板）或 **Zashboard**；
  面板经同源反代访问 Clash API，**密钥不下发前端**
- **统一网关接入**：控制台走 `/app/mihomo`，免密登录，复用 NAS 登录态
- **通道分级授权**：经网关（已登录）放行完整 Clash API；局域网直连仅放行只读白名单
- **订阅支持**：填订阅链接即可，启动时拉取并强制修正 `mixed-port` / `allow-lan` /
  `external-controller`，避免订阅内容覆盖导致局域网不可用
- **节点切换与流量监控**：面板内直接切换节点、查看实时连接
- **不使用 Docker**：内核与面板随包携带，安装即用

- 运行身份：`package`
- 最低系统版本：fnOS 1.1.3100
- ⚠️ TUN 模式未启用（需 `run-as=root`，已知 `setcap` 路线在真机被否决）
- ⚠️ 本包内含 GPL-3.0 的 mihomo 内核，随包附带许可证全文
- 详细说明：[`mihomo/README.md`](./mihomo/README.md)

---

## 3. 在飞牛里添加本应用源

1. 打开飞牛 fnOS 客户端，进入「应用中心 → 应用源 / 第三方源」。
2. 添加源，填入仓库地址：

   ```text
   https://github.com/sushazhi/FnDepot
   ```

   也可以填入 `fnpack.json` 的 JSON 直链。

3. 同步后即可在源里看到上表中的 7 个应用，按机型（x86 / arm）选择对应安装包安装。

> 客户端需 > 0.0.7 才支持 V2 源。由于飞牛已启用 httponly，旧版客户端将无法继续
> 使用，新版本已完成适配。

---

## 4. 仓库结构

```text
FnDepot/
├── fnpack.json                 # 应用源索引（V2），客户端实际读取的文件
├── config.json                 # 同步脚本的数据源清单（仓库 / 元数据 / 打包规则）
├── docs/
│   └── README.fnpack-v2-spec.md    # 《外部应用源 V2 编写说明》（原始规范，完整保留）
├── scripts/
│   └── sync_releases.py        # 拉取各仓库最新 Release，重建 fnpack.json 的 releases
├── .github/workflows/
│   └── sync-releases.yml       # 每天自动同步并提交
├── logmanager/                 # 各应用：图标、README、预览图
├── qbittorrent/
├── transmission/
├── moviepilot/
├── agent2api/
├── cli2api/
└── mihomo/
```

每个应用目录的约定结构：

```text
<app>/
├── ICON.PNG            # 应用图标（客户端卡片与详情页）
├── ICON_256.PNG        # 高分辨率图标
├── README.md           # 应用介绍（详情页「README」标签，由 readme_url 指向）
└── Preview/            # 预览图（详情页截图轮播，由 preview_urls 指向）
```

---

## 5. 版本如何更新

`fnpack.json` 里的 `releases` 由脚本自动生成，**不需要手工编辑**：

1. 上游各仓库（`sushazhi/fnos-*`）发布新的 GitHub Release 并上传 `.fpk` 后，
   `config.json` 中登记的应用会在下一次同步时自动更新。
2. 同步脚本按 `keep_latest`（当前为 4）保留每个应用最新 4 个版本，重建
   `releases` 字段；应用的静态信息（图标、README、预览图、反馈链接等）保持不变。
3. `changelog` 取自 Release 正文并做归一化：`<br>` 转成换行（客户端只认 `\n`），
   丢弃 `<b>` / `</b>` 标签与结尾的 SHA256 页脚。
4. 多架构应用的 `sha256` 优先取 GitHub 资产自带的 `digest`；单包应用则读取仓库
   发布的 `.sha256` 文件。
5. 若某个仓库的 tag 只标上游版本、而 FPK 版本号带打包修订号（如 tag `v0.6.13`
   对应 `cli2api-0.6.13-1-amd64.fpk`），在 `config.json` 里为该应用声明
   `version_from_asset: true`，脚本会从资产名回推真正的版本号；各架构版本号
   不一致时退回 tag，不会猜。
6. 本文件「[应用一览](#1-应用一览)」表格里的「最新版本」列也由同一个脚本刷新，
   所以它不会与 `fnpack.json` 漂移。**该列不要手工编辑**；如需关闭这项更新，
   在 `config.json` 里设 `update_readme_versions: false`。

手动触发：仓库 **Actions → 自动同步最新版本 → Run workflow**
（可选传入 PAT 以访问私有仓库或提高 API 速率限制）。

本地预览（只打印、不写回）：

```bash
FND_SYNC_DRY_RUN=1 python scripts/sync_releases.py
```

发布新版本时，请使用新的版本号、下载地址、大小和 SHA256，**不要静默替换同版本
FPK** —— 已发布的「版本号 + 架构」文件应视为不可变。

---

## 6. 许可与致谢

- 本仓库的打包适配、脚本与文档由 **yukihana** 维护；各应用的上游项目版权归其各自
  作者所有（`maintainer` / `maintainer_url` 字段已逐应用标注）。
- 每个应用的授权与上游信息，见该应用目录下的 `README.md` 以及 fpk 包内的
  `LICENSE` / `LICENSE.upstream` / `UPSTREAM.txt`。
- 应用源规范 V2：[《外部应用源 V2 编写说明》](./docs/README.fnpack-v2-spec.md)
