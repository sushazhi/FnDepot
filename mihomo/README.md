# Mihomo

> 把 [mihomo](https://github.com/MetaCubeX/mihomo)（Clash.Meta）代理内核做成飞牛 fnOS
> 原生应用：开机自启，提供混合代理端口 + Clash API + 内置控制面板。

上游 [MetaCubeX/mihomo](https://github.com/MetaCubeX/mihomo) 内核 + 配套适配层，
由 yukihana 打包维护。**不使用 Docker**，不需要 Node 运行时。

---

## 功能

- **开机自启**：由 fnOS 应用中心托管 `cmd/main` 的 `start` / `stop` / `status`
- **混合代理端口**（默认 `7890`）：HTTP / SOCKS5 同端口，局域网设备与容器可直接使用
- **Clash API**（默认 `9090`）：供 MetaCubeXD、Zashboard 等第三方面板与客户端连接
- **内置控制面板**：桌面入口走**统一网关** `/app/mihomo`，复用 NAS 登录态；首次点图标
  可选 **MetaCubeXD** 或 **Zashboard**；面板经同源反代访问 Clash API，**密钥不下发前端**
- **订阅支持**：在「应用设置」填订阅链接，启动时拉取并强制修正 `mixed-port` /
  `allow-lan` / `external-controller`，避免订阅内容覆盖导致局域网不可用
- **节点切换与流量监控**：面板内直接切换节点、查看实时连接与流量

---

## 访问模型：统一网关 + 独立端口

| 组件 | 访问模型 | 需要登录态 |
| --- | --- | --- |
| 内置控制面板（MetaCubeXD / Zashboard） | **统一网关** `/app/mihomo`（Unix Socket） | 是（网关强制校验） |
| 代理端口 `7890` | 独立 TCP 端口 | 否（局域网设备/容器无 cookie） |
| Clash API `9090` | 独立 TCP 端口 | 否（第三方客户端无 cookie） |

管理面板**只走统一网关**，不额外开 TCP 端口；代理端口与 Clash API 必须是独立端口，
因为它们的消费方是非浏览器客户端。三种消费者性质不同，不做一刀切。

### 面板如何免填密钥

面板需要完整 Clash API（含写操作）。本应用按**通道分级授权**：

| 通道 | 授权范围 |
| --- | --- |
| 经**统一网关**（已登录） | 放行**完整** Clash API，密钥由服务端注入 |
| **局域网直连** | 仅放行**只读白名单**（如 `/version`） |

判定依据是网关注入的 `X-Trim-Userid`。Socket 权限 `0600`，停止时自动清理。

### 怎么换面板

- 面板**右下角的「⇄ 面板」浮动按钮** —— 在 fnOS 桌面 iframe 里也能用，这是唯一不需要
  动地址栏的方式
- 或直接访问 `https://<NAS>/app/mihomo/?choose=1` 回到选择页
- 想直接进某个面板：`.../app/mihomo/panel/metacubexd/`、`.../app/mihomo/panel/zashboard/`

> ⚠️ 在面板页面地址后面手动加 `?choose=1` **不会有任何效果**。两个面板都是 PWA，
> 各自注册了 Workbox 的 `NavigationRoute`，面板内的导航请求会被 Service Worker 用
> 预缓存的 `index.html` 直接应答，请求根本到不了服务端，服务端也就没机会返回选择页。
> 切换入口必须活在面板页面自身的 DOM 里 —— 这就是那个浮动按钮存在的原因。

选择记在 `localStorage`（按浏览器隔离，多用户各自记住）。

---

## 安全说明（重要）

状态页默认绑定 `0.0.0.0`（`:9092`），供 fnOS 桌面入口与局域网访问。为此**只开放极小
只读白名单**，状态页所需数据由服务端聚合后输出：

```python
ALLOWED_PROXY_ENDPOINTS = {"/version"}
```

**刻意不开放**（避免泄露）：`/connections`（访问记录）、`/proxies`（节点名）、
`/rules`（规则集）、`/configs`（**含 secret**）。

如需更严格，可限制为本机访问：

```bash
MIHOMO_UI_BIND=127.0.0.1   # 默认 0.0.0.0
```

若确实需要局域网直连状态页，可设 `MIHOMO_UI_TCP=1` 额外监听 TCP `:9092`（默认关闭）。

---

## 运行信息

- **运行身份**：`package`（最小权限，默认不使用 root）
- **最低系统版本**：fnOS `1.1.3100`
- **架构**：`x86`（amd64）/ `arm`（arm64）分别出包，不使用 `all`
  —— 包内含按固定路径加载的原生二进制，无法在运行期分派
- **持久化**：配置与订阅存放于应用数据目录，升级与重装保留

---

## 已知取舍

- **TUN 模式未启用**：需要 `/dev/net/tun` 与 `CAP_NET_ADMIN`，而 `config/privilege`
  没有 capability 字段。已实测「保持 package 用户 + `setcap`」路线在真机被否决
  （四个前置条件全部满足，但已打 capability 与未打的副本得到完全相同的 EPERM，
  file capability 未生效）。**TUN 若要做只能 `run-as=root`**，代价是把面板、订阅解析、
  Clash API 全部拉进 root。本应用因此默认走代理端口模式。
- **默认分架构**：为避免装错架构导致「装得上但起不来」，`platform` 分 x86 / arm
  分别打包。

---

## 许可

mihomo 内核采用 **GPL-3.0**；本应用的适配脚手架部分可自由使用。
本包内含 mihomo 内核，随包附带许可证全文并在安装时展示协议。
内核版权归 [MetaCubeX](https://github.com/MetaCubeX/mihomo) 所有。
