#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_releases.py — 自动同步 GitHub Release 到 fnpack.json

工作原理
--------
1. 读取仓库根目录的 config.json（数据源清单，列出要跟踪的 GitHub 仓库与应用元数据）。
2. 逐个应用调用 GitHub API 拉取该仓库最新的 N 个正式 Release（N = config.keep_latest）。
3. 按应用规则（asset_name_pattern / arch_suffix / sha256_asset）重建 fnpack.json 中
   该应用的 `releases` 字段；应用的其余静态字段（图标、README、预览图、反馈链接等）保持不变。
   changelog 取 Release 正文并做归一化：`<br>` 换成换行（客户端只认 `\n`），丢弃 `<b>`/`</b>`
   与结尾的 SHA256 页脚。
4. 将结果写回 fnpack.json（UTF-8，无 BOM，缩进 2，保留中文）。

仅依赖 Python 标准库，无需安装第三方包。

环境变量
--------
- GITHUB_TOKEN: 可选。提供后 API 速率限制提升为 5000 次/小时，且可访问私有仓库。
  未提供时使用匿名访问（公开仓库 60 次/小时）。
- FND_SYNC_DRY_RUN: 若设为 1/true/yes，则只打印结果不写回 fnpack.json（用于预览）。
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.json")
FNPACK_PATH = os.path.join(ROOT, "fnpack.json")
API_BASE = "https://api.github.com"
BEIJING_TZ = timezone(timedelta(hours=8))
SHA256_RE = re.compile(r"\b[0-9a-f]{64}\b")
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
BOLD_RE = re.compile(r"</?b\s*>", re.IGNORECASE)
SHA256_FOOTER_RE = re.compile(r"(?:\r?\n)+\s*-{3,}\s*(?:\r?\n)+\s*\*\*SHA256:", re.IGNORECASE)
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()


def log(msg: str) -> None:
    print(msg, flush=True)


def http_get(url: str, token: str = "", is_json: bool = True):
    """GET 请求。token 非空时附带 Authorization 头。返回 (body_bytes, content_type)。"""
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json" if is_json else "*/*",
        "User-Agent": "FnDepot-SyncBot",
    })
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {e.code} for {url}: {body[:300]}") from e


def version_key(tag: str):
    """把 tag 变成可比较的版本排序键。'v1.2.3.2' -> (1,2,3,2)；无法解析的段用 -1 兜底。"""
    v = tag.lstrip("vV")
    parts = re.split(r"[.\-]", v)
    out = []
    for p in parts:
        m = re.match(r"^\d+$", p)
        out.append(int(p) if m else -1)
    return tuple(out)


def to_beijing_iso(published_at: str) -> str:
    """'2026-09-11T13:28:28Z' -> '2026-09-11T21:28:28+08:00'。"""
    dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    return dt.astimezone(BEIJING_TZ).isoformat()


def fetch_releases(owner: str, repo: str, keep: int) -> list:
    """拉取最新 keep 个 Release（GitHub 返回即按发布时间倒序）。"""
    url = f"{API_BASE}/repos/{owner}/{repo}/releases?per_page={keep}&page=1"
    body, _ = http_get(url, TOKEN)
    data = json.loads(body.decode("utf-8"))
    # 过滤草稿；默认忽略预发布（除非 config 里显式 include_prerelease=True）
    out = []
    for r in data:
        if r.get("draft"):
            continue
        out.append(r)
    return out


def parse_sha256(raw: bytes) -> str:
    """从 .sha256 文件内容里取出 64 位十六进制摘要，容忍 BOM / 文件名 / 换行。"""
    text = raw.decode("utf-8", "replace").replace("\ufeff", "").strip()
    m = SHA256_RE.search(text)
    return m.group(0) if m else None


def normalize_changelog(body: str) -> str:
    """Release 正文归一化成 changelog：<br> 换成换行，去掉 <b>/</b> 与结尾的 SHA256 页脚。"""
    text = BR_RE.sub("\n", body)
    text = BOLD_RE.sub("", text)
    m = SHA256_FOOTER_RE.search(text)
    if m:
        text = text[:m.start()]
    return text.strip()


def build_packages(app: dict, release: dict, owner: str, repo: str) -> dict:
    """根据应用规则与 Release 的资产，构建 packages 字段。"""
    key = app["key"]
    tag = release["tag_name"]
    version = tag.lstrip("vV")
    assets = release.get("assets", [])
    assets_by_name = {a["name"]: a for a in assets}

    arch_suffix = app.get("arch_suffix") or {}
    packages = {}

    if arch_suffix:
        # 多架构：按 arch_suffix 为每种架构生成一份包，命名 {key}-{ver}{suffix}.fpk
        for arch, suffix in arch_suffix.items():
            name = f"{key}-{version}{suffix}.fpk"
            a = assets_by_name.get(name)
            if a is None:
                log(f"    [跳过] {repo} {tag} 未找到资产 {name}")
                continue
            pkg = {
                "download_url": a["browser_download_url"],
                "size": a["size"],
            }
            packages[arch] = pkg
    else:
        # 单包（通用 all 包）：命名取自 asset_name_pattern，默认 {key}-{ver}.fpk
        pattern = app.get("asset_name_pattern") or f"{key}-{{ver}}.fpk"
        name = pattern.replace("{ver}", version)
        a = assets_by_name.get(name)
        if a is None:
            log(f"    [跳过] {repo} {tag} 未找到资产 {name}")
            return packages
        pkg = {
            "download_url": a["browser_download_url"],
            "size": a["size"],
        }
        # 可选：从 .sha256 资产读取摘要
        sha_pattern = app.get("sha256_asset", "")
        if sha_pattern:
            sha_name = sha_pattern.replace("{ver}", version)
            sha_asset = assets_by_name.get(sha_name)
            if sha_asset:
                raw, _ = http_get(sha_asset["browser_download_url"], TOKEN, is_json=False)
                sha = parse_sha256(raw)
                if sha:
                    pkg["sha256"] = sha
                else:
                    log(f"    [警告] {repo} {tag} 无法从 {sha_name} 解析 SHA256")
            else:
                log(f"    [跳过] {repo} {tag} 未找到 sha256 资产 {sha_name}")
        packages["all"] = pkg

    return packages


def default_app_from_config(app: dict, owner: str = "") -> dict:
    """当 fnpack 中尚不存在该应用时，用 config 生成一个默认应用节点。"""
    key = app["key"]
    repo = app.get("repo", "")
    slug = f"{owner}/{repo}" if owner and repo else repo
    base = {
        "display_name": app.get("display_name", key),
        "desc": app.get("desc", ""),
        "platform": app.get("platform", ["all"]),
        "categories": app.get("categories", []),
        "icon_url": f"./{key}/ICON.PNG",
        "readme_url": f"./{key}/README.md",
        "bug_report_url": f"https://github.com/{slug}/issues" if slug else "",
        "maintainer": app.get("maintainer", ""),
        "maintainer_url": app.get("maintainer_url", ""),
        "distributor": app.get("distributor", ""),
        "distributor_url": app.get("distributor_url", ""),
        "run_as": app.get("run_as", "package"),
        "install_type": app.get("install_type", ""),
        "is_docker": app.get("is_docker", False),
        "service_port": app.get("service_port", ""),
        "releases": {},
    }
    if app.get("preview_urls"):
        base["preview_urls"] = app["preview_urls"]
    return base


def main() -> int:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    with open(FNPACK_PATH, "r", encoding="utf-8") as f:
        fnpack = json.load(f)

    owner = config.get("github_owner", "")
    keep = int(config.get("keep_latest", 4))
    include_prerelease = bool(config.get("include_prerelease", False))

    dry_run = os.environ.get("FND_SYNC_DRY_RUN", "").lower() in ("1", "true", "yes")

    apps = fnpack.setdefault("apps", {})
    total_versions = 0

    for app in config.get("apps", []):
        repo = app.get("repo")
        key = app.get("key")
        if not repo or not key:
            log(f"[警告] config 中应用缺少 repo/key，跳过：{app}")
            continue
        log(f"同步 {key} <- {owner}/{repo} (保留最新 {keep} 个)")

        releases = fetch_releases(owner, repo, keep)
        if not include_prerelease:
            releases = [r for r in releases if not r.get("prerelease")]

        # 按版本号倒序，取前 keep 个
        releases = sorted(releases, key=lambda r: version_key(r["tag_name"]), reverse=True)[:keep]

        new_releases = {}
        for r in releases:
            tag = r["tag_name"]
            version = tag.lstrip("vV")
            packages = build_packages(app, r, owner, repo)
            if not packages:
                log(f"    [跳过] {repo} {tag} 无可用资产，不写入")
                continue
            entry = {}
            changelog = normalize_changelog(r.get("body") or "")
            if changelog:
                entry["changelog"] = changelog
            if r.get("published_at"):
                entry["updated_at"] = to_beijing_iso(r["published_at"])
            if app.get("os_min_version"):
                entry["os_min_version"] = app["os_min_version"]
            entry["packages"] = packages
            new_releases[version] = entry

        # 合并进 fnpack：保留该应用的静态字段，仅重建 releases
        if key not in apps:
            apps[key] = default_app_from_config(app, owner)
        node = apps[key]
        # 用 config 中提供的权威字段覆盖静态信息（保持配置为准）
        for field in ("display_name", "desc", "platform", "categories",
                      "maintainer", "maintainer_url", "distributor",
                      "distributor_url", "run_as", "install_type",
                      "is_docker", "service_port"):
            if field in app:
                node[field] = app[field]
        node["releases"] = new_releases
        total_versions += len(new_releases)
        log(f"    -> 写入 {len(new_releases)} 个版本：{list(new_releases.keys())}")

    if dry_run:
        log(f"[dry-run] 不写回 fnpack.json。预览内容：\n{json.dumps(fnpack, ensure_ascii=False, indent=2)}")
        return 0

    with open(FNPACK_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(fnpack, f, ensure_ascii=False, indent=2)
        f.write("\n")
    log(f"完成：已写回 {FNPACK_PATH}，共更新 {total_versions} 个版本。")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        log(f"错误：{e}")
        sys.exit(1)
