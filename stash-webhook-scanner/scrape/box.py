"""stash-box 统一刮削代理（2026-08-17）。

一个模块，两个应用（JAV / Non-JAV）：
- 指纹直连查库（findScenesBySceneFingerprints，OSHASH+PHASH）
- 9999 scrapeSingleScene 按 stash_id 拉全量（格式统一）
- 多源合并（单值主源优先、多值合并去重）

设计：DESIGN-nonjav-scrape.md
"""

import asyncio
import io
import logging
import re
import struct
from collections import Counter

import httpx

from config import Config
from stash import query as Q
from stash import tag as tag_mod
from stash import performer as performer_mod
from stash import studio as studio_mod
from stash import scene as scene_mod
from scrape.sources import (
    NONJAV_SOURCES,
    JAV_SOURCES,
    JAV_CROSSREF_SOURCES,
    FINGERPRINT_SOURCES,
    ScrapeSource,
    get_primary,
    get_source_by_name,
)

logger = logging.getLogger(__name__)

# 外网代理（直连 stashdb/theporndb 统一走这条）
STASHBOX_PROXY = getattr(Config, "STASHBOX_PROXY", "http://<proxy>:7890")

# ── 工具函数 ──────────────────────────────────────


def _get_stashbox_key(client, endpoint: str) -> str | None:
    """从 Stash 配置中动态获取指定 endpoint 的 API key。"""
    config = client.config_cache
    if not config:
        return None
    boxes = (
        config.get("configuration", {})
        .get("general", {})
        .get("stashBoxes", [])
    )
    for b in boxes:
        ep = b.get("endpoint", "").rstrip("/")
        if ep == endpoint.rstrip("/"):
            return b.get("api_key")
    return None


async def _ensure_config_cache(client):
    """确保 client.config_cache 缓存了配置（包含 stashBoxes key）。"""
    if not getattr(client, "config_cache", None):
        data = await client.post("""
            query GetConfig {
              configuration { general { stashBoxes { endpoint api_key } } }
            }
        """, {})
        if data:
            client.config_cache = data


async def _get_scene_fingerprints(client, scene_id: str) -> dict:
    """从 Stash 获取场景的 oshash + phash（files.fingerprints）。"""
    data = await client.post("""
        query($id: ID!) {
          findScene(id: $id) {
            files { fingerprints { type value } }
          }
        }
    """, {"id": scene_id})
    if not data:
        return {}
    scene = data.get("findScene") or {}
    fp = {}
    for f in (scene.get("files") or []):
        for fprint in (f.get("fingerprints") or []):
            t = fprint.get("type", "").lower()
            v = fprint.get("value")
            if t in ("oshash", "phash") and v and t not in fp:
                fp[t] = v
    return fp


# ── 指纹查库（直连 stash-box） ─────────────────────


async def _fingerprint_search(
    source: ScrapeSource,
    fprints: dict,
    client,
) -> str | None:
    """调用 stash-box 的 findScenesBySceneFingerprints，返回 stash_id 或 None。"""
    key = _get_stashbox_key(client, source.endpoint)
    if not key:
        logger.warning("      - ⚠️ %s: 无 API key，跳过", source.name)
        return None

    groups = []
    for algo in ("OSHASH", "PHASH"):
        val = fprints.get(algo.lower())
        if val:
            groups.append([{"algorithm": algo, "hash": val}])
    if not groups:
        return None

    query = """
    query($fp: [[FingerprintQueryInput!]!]!) {
      findScenesBySceneFingerprints(fingerprints: $fp) { id }
    }
    """
    try:
        r = httpx.post(
            source.endpoint,
            json={"query": query, "variables": {"fp": groups}},
            timeout=30,
            proxy=STASHBOX_PROXY,
            verify=False,
            headers={"ApiKey": key},
        )
        data = r.json()
    except Exception as e:
        logger.warning("      - ⚠️ %s 指纹查询异常: %s", source.name, e)
        return None

    if "errors" in data:
        logger.warning("      - ⚠️ %s 指纹查询错误: %s", source.name, data["errors"])
        return None

    results = data.get("data", {}).get("findScenesBySceneFingerprints", [])
    for group in results:
        if group:
            return group[0]["id"]
    return None


async def fingerprint_detect(client, scene_id: str) -> dict:
    """指纹预查三源（javstash/stashdb/theporndb），用于 JAV/Non-JAV 判定（2026-08-19）。

    只做指纹查库，返回每个已配置源的命中 stash_id，不拉全量：
        {
            "javstash":   "uuid" | None,
            "stashdb":    "uuid" | None,
            "theporndb":  "uuid" | None,
        }

    判定规则（供 pipeline 分流用）：
      - javstash 命中 → JAV（stashdb/tpdb 只作信息补充）
      - javstash 未命中但 stashdb/tpdb 命中 → Non-JAV
      - 全部未命中 → None（回退文件名/番号检测）
    """
    await _ensure_config_cache(client)
    fprints = await _get_scene_fingerprints(client, scene_id)
    if not fprints:
        logger.warning("   - 🔑 场景 %s 无指纹，无法指纹预查", scene_id)
        return {}
    logger.info("   - 🔑 指纹预查: oshash=%s phash=%s",
                fprints.get("oshash", "")[:12], fprints.get("phash", "")[:12])

    hits = {}
    # javstash 优先，stashdb/tpdb 补充
    probe_sources = (get_source_by_name("javstash"),) + tuple(
        get_source_by_name(n) for n in ("stashdb", "theporndb")
        if get_source_by_name(n)
    )
    for src in probe_sources:
        if not src or not src.fingerprint_supported:
            continue
        sid = await _fingerprint_search(src, fprints, client)
        hits[src.name] = sid
        if sid:
            logger.info("   - ✅ 指纹命中 %s: %s", src.name, sid)
        else:
            logger.info("   - ⏭️ 指纹未命中 %s", src.name)
    return hits


# ── 9999 拉全量数据 ───────────────────────────────


async def _fetch_full(client, source: ScrapeSource, stash_id: str, scene_id: str) -> dict | None:
    """通过 Stash 9999 scrapeSingleScene 按 stash_id 拉全量 ScrapedScene。"""
    variables = {
        "source": {"stash_box_endpoint": source.endpoint},
        "input": {
            "scene_id": scene_id,
            "scene_input": {"remote_site_id": stash_id},
        },
    }
    try:
        data = await client.post(Q.SCRAPE_SINGLE_SCENE, variables)
    except Exception as e:
        logger.warning("      - ⚠️ %s 全量拉取异常: %s", source.name, e)
        return None
    if not data:
        return None
    scenes = data.get("scrapeSingleScene")
    if not scenes:
        return None
    if isinstance(scenes, list):
        if not scenes:
            return None
        # 优先取 remote_site_id 精确匹配的
        for s in scenes:
            if s.get("remote_site_id") == stash_id:
                return s
        return scenes[0]
    return scenes


# ── 图片下载与分辨率比较 ────────────────────────────


def _parse_image_dimensions(data: bytes, content_type: str) -> tuple[int, int]:
    """解析图片尺寸 (width, height)。支持 JPEG/PNG/WebP。"""
    ct = content_type.lower()
    if "png" in ct and len(data) >= 24:
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    if "jpeg" in ct or "jpg" in ct:
        # 查找 SOF0 / SOF1 / SOF2 标记
        i = 0
        while i < len(data) - 1:
            if data[i] == 0xFF and data[i + 1] in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 1
        return 0, 0
    if "webp" in ct and len(data) >= 30:
        # VP8X: 偏移 24 字节有宽高
        w = struct.unpack("<H", data[26:28])[0] | ((data[24] & 0x3F) << 16 if len(data) > 24 else 0)
        h = struct.unpack("<H", data[28:30])[0] | ((data[24] & 0xC0) << 8 if len(data) > 24 else 0)
        return w, h
    if "svg" in ct:
        # 提取 viewBox 尺寸
        m = re.search(r'viewBox="\d+\s+\d+\s+([\d.]+)\s+([\d.]+)"', data.decode("utf-8", errors="ignore"))
        if m:
            return int(float(m.group(1))), int(float(m.group(2)))
        return 0, 0
    return 0, 0


async def _download_image(url: str) -> tuple[bytes, str, int, int]:
    """下载图片，返回 (data, content_type, width, height)。"""
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            proxy=STASHBOX_PROXY,
            verify=False,
            follow_redirects=True,
        ) as c:
            r = await c.get(url)
            r.raise_for_status()
            ct = r.headers.get("content-type", "image/jpeg")
            data = r.content
            w, h = _parse_image_dimensions(data, ct)
            return data, ct, w, h
    except Exception as e:
        logger.warning("      - ⚠️ 图片下载失败: %s | %s", url[:80], e)
        return b"", "", 0, 0


async def _pick_best_image(*urls: str) -> str | None:
    """下载所有图片，返回分辨率最大的那张的 base64 data URL。

    支持两种格式：
    - data:image/...  base64 data URL → 直接解码读分辨率
    - https://... 普通 URL → 下载后读分辨率
    """
    import base64

    best_data = None
    best_area = 0
    for url in urls:
        if not url:
            continue

        data = b""
        ct = ""
        if url.startswith("data:"):
            # data URL: format = data:image/jpeg;base64,<base64>
            try:
                _, b64part = url.split(",", 1)
                data = base64.b64decode(b64part)
                ct = url.split(";")[0].split(":")[1] if ";" in url else "image/jpeg"
            except Exception as e:
                logger.warning("      - ⚠️ data URL 解码失败: %s", e)
                continue
        else:
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(30.0),
                    proxy=STASHBOX_PROXY,
                    verify=False,
                    follow_redirects=True,
                ) as c:
                    r = await c.get(url)
                    r.raise_for_status()
                    data = r.content
                    ct = r.headers.get("content-type", "image/jpeg")
            except Exception as e:
                logger.warning("      - ⚠️ 图片下载失败: %s | %s", url[:80], e)
                continue

        if not data:
            continue
        w, h = _parse_image_dimensions(data, ct)
        area = w * h
        if area > best_area:
            best_area = area
            best_data = data
            logger.info("      - 🖼️ 图片优先级更新: %dx%d (%s) %s", w, h, ct, url[:60])

    if best_data:
        return "data:image/jpeg;base64," + base64.b64encode(best_data).decode("ascii")
    return None


# ── 演员匹配（URL 交叉引用 / 名称） ──────────────────


def _performer_ids_from_urls(urls, domain):
    """提取 urls 中指向指定域名 /performers/<id> 的 id 集合。"""
    ids = set()
    for u in urls or []:
        if domain not in u or "/performers/" not in u:
            continue
        pid = u.rstrip("/").rsplit("/", 1)[-1]
        if pid:
            ids.add(pid.lower())
    return ids


def _match_performer_by_url(perf_a: dict, source_a: ScrapeSource,
                             perf_b: dict, source_b: ScrapeSource) -> bool:
    """通过 URL 交叉引用判断两个站点的演员是否为同一人。

    ⚠️ 2026-08-18 修复：不能只检查域名出现（stashdb 的 performer urls 常含
    theporndb.net 任意链接，误配）。必须解析 URL 末段 performer id，
    与对方的 remote_site_id 精确比对。
    """
    def _performer_ids_from_urls(urls, domain):
        """提取 urls 中指向指定域名 /performers/<id> 的 id 集合。"""
        ids = set()
        for u in urls or []:
            if domain not in u or "/performers/" not in u:
                continue
            pid = u.rstrip("/").rsplit("/", 1)[-1]
            if pid:
                ids.add(pid.lower())
        return ids

    # A 的 urls 里指向 B 域的 performer id，是否等于 B 的 remote_site_id
    ids_a_to_b = _performer_ids_from_urls(perf_a.get("urls"), source_b.domain)
    if ids_a_to_b and perf_b.get("remote_site_id"):
        return (perf_b["remote_site_id"].lower() in ids_a_to_b)

    # B 的 urls 里指向 A 域的 performer id，是否等于 A 的 remote_site_id
    ids_b_to_a = _performer_ids_from_urls(perf_b.get("urls"), source_a.domain)
    if ids_b_to_a and perf_a.get("remote_site_id"):
        return (perf_a["remote_site_id"].lower() in ids_b_to_a)

    return False


def _match_performer_by_name(perf_a: dict, perf_b: dict) -> bool:
    """按演员名（含别名）判断是否为同一人。"""
    name_a = (perf_a.get("name") or "").lower().strip()
    name_b = (perf_b.get("name") or "").lower().strip()
    if name_a and name_a == name_b:
        return True
    # 别名检查
    aliases_a = [a.lower().strip() for a in (perf_a.get("aliases") or [])]
    if name_b in aliases_a:
        return True
    aliases_b = [a.lower().strip() for a in (perf_b.get("aliases") or [])]
    if name_a in aliases_b:
        return True
    return False


async def _merge_performers(primary_list: list, secondary_list: list,
                      primary_source: ScrapeSource,
                      secondary_source: ScrapeSource) -> list:
    """合并两个站点演员列表：交叉引用匹配 → 合并去重 → 多源 stash_ids。"""
    merged = []
    used_secondary = set()

    for pa in primary_list:
        name_a = (pa.get("name") or "").lower().strip()
        if not name_a:
            continue
        matched = None
        for i, pb in enumerate(secondary_list):
            if i in used_secondary:
                continue
            if _match_performer_by_url(pa, primary_source, pb, secondary_source) or \
               _match_performer_by_name(pa, pb):
                matched = pb
                used_secondary.add(i)
                break
        if matched:
            # 合并：pa 为主，matched 补充
            merged.append(await _merge_performer_pair(pa, matched, primary_source, secondary_source))
        else:
            merged.append(pa)  # 只有主站数据

    # 添加未匹配的次站演员
    for i, pb in enumerate(secondary_list):
        if i not in used_secondary:
            merged.append(pb)

    return merged


async def _merge_performer_pair(primary: dict, secondary: dict,
                          primary_source: ScrapeSource,
                          secondary_source: ScrapeSource) -> dict:
    """合并两个站点的同一演员数据。"""
    result = dict(primary)

    # stash_ids：两家的都填
    stash_ids = []
    if primary.get("remote_site_id"):
        stash_ids.append({"endpoint": primary_source.endpoint, "stash_id": primary["remote_site_id"]})
    if secondary.get("remote_site_id"):
        stash_ids.append({"endpoint": secondary_source.endpoint, "stash_id": secondary["remote_site_id"]})
    if stash_ids:
        result["stash_ids"] = stash_ids

    # 单值字段：primary 优先，secondary 补缺
    for field in ("birthdate", "country", "ethnicity", "eye_color", "hair_color",
                   "fake_tits", "career_start", "career_end", "disambiguation"):
        if not result.get(field) and secondary.get(field):
            result[field] = secondary[field]

    # 身高：取非空值
    if not result.get("height") and secondary.get("height"):
        result["height"] = secondary["height"]

    # 多值字段：合并去重
    result["urls"] = _merge_urls(primary.get("urls", []) or [], secondary.get("urls", []) or [])
    result["aliases"] = _merge_unique(
        primary.get("aliases", []) or [],
        secondary.get("aliases", []) or [],
    )
    # images：取主站的，次站补缺
    if not result.get("images") and secondary.get("images"):
        result["images"] = secondary["images"]

    # 简介（theporndb 网页 bio；GraphQL 不暴露，需登录抓取）
    # 主源为 theporndb 时直接用其 remote_site_id；否则尝试 theporndb 侧的 id
    tp_id = None
    if secondary_source.name == "theporndb" and secondary.get("remote_site_id"):
        tp_id = secondary["remote_site_id"]
    elif primary_source.name == "theporndb" and primary.get("remote_site_id"):
        tp_id = primary["remote_site_id"]
    if tp_id and not result.get("details"):
        bio = await fetch_performer_bio(tp_id)
        if bio:
            result["details"] = bio

    return result


# ── theporndb 简介抓取（登录网页 bio，GraphQL 不暴露）─────────────────

_tp_session = None  # 模块级缓存登录 session


def _get_tp_session():
    """登录 theporndb 获取 session（带缓存）。返回 httpx.Client 或 None。"""
    global _tp_session
    if _tp_session is not None:
        return _tp_session
    if not Config.TPDB_EMAIL or not Config.TPDB_PASSWORD:
        logger.debug("TPDB 凭据未配置，跳过简介抓取")
        return None
    try:
        import urllib.parse
        c = httpx.Client(
            timeout=30, proxy=Config.TPDB_PROXY, verify=False,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        r = c.get("https://theporndb.net/login")
        xsrf = c.cookies.get("XSRF-TOKEN")
        if not xsrf:
            logger.warning("TPDB 登录页无 XSRF token")
            return None
        r = c.post(
            "https://theporndb.net/login",
            data={"email": Config.TPDB_EMAIL, "password": Config.TPDB_PASSWORD},
            headers={
                "X-XSRF-TOKEN": urllib.parse.unquote(xsrf),
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json",
            },
        )
        if r.status_code != 200 or "two_factor" not in r.text:
            logger.warning("TPDB 登录失败 status=%s", r.status_code)
            return None
        _tp_session = c
        logger.info("✅ theporndb 登录成功")
        return c
    except Exception as e:
        logger.warning("TPDB 登录异常: %s", e)
        return None


async def fetch_performer_bio(tp_performer_id: str) -> str | None:
    """抓取 theporndb performer 简介（登录后网页 bio 字段）。失败返回 None（静默跳过）。"""
    if not tp_performer_id:
        return None
    try:
        c = _get_tp_session()
        if c is None:
            return None
        import re, html as h, json as _json
        r = c.get("https://theporndb.net/performers/%s" % tp_performer_id)
        if r.status_code != 200:
            logger.warning("TPDB performer 页面 %s status=%s", tp_performer_id, r.status_code)
            return None
        m = re.search(r'<script[^>]*data-page[^>]*>(.*?)</script>', r.text, re.S)
        if not m:
            logger.warning("TPDB performer 页面 %s 无 data-page", tp_performer_id)
            return None
        raw = h.unescape(m.group(1))
        bio = None
        # bio 可能含裸引号（如 6'5"）导致 JSON 整体解析失败——用正则直接抠 bio 值
        # 匹配 "bio":"..."; bio 值内引号已由 Inertia 转义为 \"
        for pat in (
            r'"bio"\s*:\s*"((?:[^"\\]|\\.)*)"',
            r"\"bio\"\s*:\s*\"((?:[^\"\\]|\\.)*)\"",
        ):
            bm = re.search(pat, raw)
            if bm:
                bio = bm.group(1)
                break
        if not bio:
            return None
        # 反转义 \" → "，\n → 换行，\uXXXX → Unicode
        bio = bio.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
        try:
            bio = bio.encode("utf-8").decode("unicode_escape")
        except Exception:
            pass
        bio = bio.strip()
        if bio:
            logger.info("      - 📝 抓取 TPDB 简介: %s (%d 字符)", tp_performer_id[:8], len(bio))
            return bio
        return None
    except Exception as e:
        logger.warning("TPDB 简介抓取异常 %s: %s", tp_performer_id, e)
        return None


# ── 通用合并工具 ──────────────────────────────────


def _merge_urls(*url_lists) -> list:
    """合并多个 URL 列表，去重。"""
    seen = set()
    result = []
    for urls in url_lists:
        for u in urls:
            if u and u not in seen:
                seen.add(u)
                result.append(u)
    return result


def _merge_unique(*lists) -> list:
    """合并字符串列表，去重（忽略大小写，保留首次出现的）。

    ⚠️ 2026-08-18 修复：stash-box 返回的 aliases 是**逗号分隔字符串**
    （如 "Stella 791, Stella Lux, Stella"），不是数组——直接迭代字符串会
    逐字符拆分（'S','t','e','l','l','a'...）。统一先 split(',') 再合并。
    """
    seen = set()
    result = []
    for lst in lists:
        items = lst
        if isinstance(lst, str):
            items = [a.strip() for a in lst.split(",") if a.strip()]
        for item in items or []:
            key = item.lower().strip()
            if key and key not in seen:
                seen.add(key)
                result.append(item)
    return result


def _merge_tags(tags_a: list, tags_b: list, client) -> list:
    """合并两个站点的标签列表，去重（含别名规范化）。"""
    # 直接用 tag 模块的别名判断
    # 由于这是同步函数但 tag 操作是异步的，这里只做简单去重
    # 别名去重由 write 阶段 update_scene_metadata 里的 compare_tags 处理
    seen_names = set()
    result = []
    for tag_list in (tags_a, tags_b):
        for t in tag_list:
            name = t.get("name") if isinstance(t, dict) else t
            if name and name not in seen_names:
                seen_names.add(name)
                result.append({"name": name})
    return result


# ── 主合并入口 ────────────────────────────────────


async def _merge_scraped(
    scraped_primary: dict | None,
    scraped_secondary: dict | None,
    primary_source: ScrapeSource,
    secondary_source: ScrapeSource,
    scene_id: str,
    client,
) -> dict | None:
    """合并两个站点刮削数据，返回合并后的 ScrapedScene dict。"""
    if not scraped_primary and not scraped_secondary:
        return None
    if not scraped_primary:
        return scraped_secondary
    if not scraped_secondary:
        return scraped_primary

    result = {}

    # 单值字段：主源优先，次源补缺
    for field in ("title", "code", "date", "details", "director"):
        val = scraped_primary.get(field)
        if not val:
            val = scraped_secondary.get(field)
        if val:
            result[field] = val

    # remote_site_id：主源的
    if scraped_primary.get("remote_site_id"):
        result["remote_site_id"] = scraped_primary["remote_site_id"]

    # ── 封面：下载两站，比分辨率 ──
    primary_img = scraped_primary.get("image")
    secondary_img = scraped_secondary.get("image")
    if primary_img or secondary_img:
        logger.info("      - 🖼️ 下载封面比较分辨率...")
        cover = await _pick_best_image(primary_img, secondary_img)
        if cover:
            result["image"] = cover

    # ── 工作室（含上级递归） ──
    studio_primary = scraped_primary.get("studio")
    studio_secondary = scraped_secondary.get("studio")
    result["studio"] = await _merge_studio(
        studio_primary, studio_secondary,
        primary_source, secondary_source,
        client, scene_id,
    )

    # ── 演员 ──
    performers_p = scraped_primary.get("performers") or []
    performers_s = scraped_secondary.get("performers") or []
    result["performers"] = await _merge_performers(
        performers_p, performers_s,
        primary_source, secondary_source,
    )

    # ── 标签：合并去重 ──
    tags_p = scraped_primary.get("tags") or []
    tags_s = scraped_secondary.get("tags") or []
    result["tags"] = _merge_tags(tags_p, tags_s, client)

    # ── URL：合并去重 ──
    urls_p = scraped_primary.get("urls") or []
    urls_s = scraped_secondary.get("urls") or []
    result["urls"] = _merge_urls(urls_p, urls_s)

    # ── stash_ids：两家的都填（同演员级别的 _merge_performer_pair 逻辑）──
    stash_ids = []
    if scraped_primary.get("remote_site_id"):
        stash_ids.append({"endpoint": primary_source.endpoint, "stash_id": scraped_primary["remote_site_id"]})
    if scraped_secondary.get("remote_site_id"):
        stash_ids.append({"endpoint": secondary_source.endpoint, "stash_id": scraped_secondary["remote_site_id"]})
    if stash_ids:
        result["stash_ids"] = stash_ids

    return result


async def _merge_studio(
    studio_primary: dict | None,
    studio_secondary: dict | None,
    primary_source: ScrapeSource,
    secondary_source: ScrapeSource,
    client,
    scene_id: str,
) -> dict | None:
    """合并工作室数据（含直连查 parent/image/urls 递归）。"""
    if not studio_primary and not studio_secondary:
        return None
    if not studio_primary:
        return studio_secondary
    if not studio_secondary:
        return studio_primary

    name = studio_primary.get("name") or studio_secondary.get("name")
    if not name:
        return studio_primary

    # 合并 stash_ids
    stash_ids = []
    if studio_primary.get("remote_site_id"):
        stash_ids.append({"endpoint": primary_source.endpoint, "stash_id": studio_primary["remote_site_id"]})
    if studio_secondary.get("remote_site_id") and \
       studio_secondary["remote_site_id"] != studio_primary.get("remote_site_id"):
        stash_ids.append({"endpoint": secondary_source.endpoint, "stash_id": studio_secondary["remote_site_id"]})

    # 9999 返回的 studio 数据不足（无 image/urls/parent），直连 API 补充
    detail_p = None
    if studio_primary.get("remote_site_id"):
        detail_p = await _fetch_studio_detail(client, primary_source, studio_primary["remote_site_id"])
    detail_s = None
    if studio_secondary.get("remote_site_id") and \
       (not detail_p or studio_secondary["remote_site_id"] != studio_primary.get("remote_site_id")):
        detail_s = await _fetch_studio_detail(client, secondary_source, studio_secondary["remote_site_id"])

    # URLs
    urls = _merge_urls(
        (detail_p or {}).get("urls", []),
        (detail_s or {}).get("urls", []),
    )

    # 图片：优先直连的 image URL（HTTP 下载），次选 9999 的（可能是 data URL）
    image_urls = []
    for d in (detail_p, detail_s):
        if d and d.get("image_url"):
            image_urls.append(d["image_url"])
    best_img = None
    if image_urls:
        logger.info("      - 🏢 下载工作室 logo 比较分辨率...")
        best_img = await _pick_best_image(*image_urls)

    # 父工作室
    parent = None
    for d in (detail_p, detail_s):
        if d and d.get("parent"):
            parent = d["parent"]
            break

    result = {
        "name": name,
        "urls": urls,
        "image": best_img,
        "remote_site_id": studio_primary.get("remote_site_id"),
        "stash_ids": stash_ids if stash_ids else None,
    }
    if parent:
        result["parent"] = parent
    return result


# ── 直连 stash-box 查询演员 ─────────────────────────


async def _fetch_performer_detail(client, source: ScrapeSource, stash_id: str) -> dict | None:
    """直连 stash-box 查询演员详情。返回格式兼容 _merge_performer_pair。"""
    key = _get_stashbox_key(client, source.endpoint)
    if not key:
        return None
    query = """
    query($id: ID!) {
      findPerformer(id: $id) {
        id name disambiguation aliases gender
        urls { url }
        images { id url }
        birthdate { date }
        ethnicity country eye_color hair_color
        height measurements { waist hip }
        career_start_year career_end_year
      }
    }
    """
    try:
        r = httpx.post(
            source.endpoint,
            json={"query": query, "variables": {"id": stash_id}},
            timeout=30,
            proxy=STASHBOX_PROXY,
            verify=False,
            headers={"ApiKey": key},
        )
        data = r.json()
    except Exception as e:
        logger.warning("      - ⚠️ 查询演员详情异常: %s", e)
        return None
    if "errors" in data:
        logger.warning("      - ⚠️ 查询演员详情错误: %s", data["errors"])
        return None
    perf = data.get("data", {}).get("findPerformer")
    if not perf:
        return None

    result = {"remote_site_id": perf["id"]}
    if perf.get("name"):
        result["name"] = perf["name"]
    if perf.get("disambiguation"):
        result["disambiguation"] = perf["disambiguation"]
    if perf.get("aliases"):
        # stash-box aliases 可能是逗号分隔字符串，_merge_unique 会处理
        result["aliases"] = perf["aliases"]
    if perf.get("gender"):
        result["gender"] = perf["gender"]

    urls = [u["url"] for u in (perf.get("urls") or []) if u.get("url")]
    if urls:
        result["urls"] = urls

    images = [img["url"] for img in (perf.get("images") or []) if img.get("url")]
    if images:
        result["images"] = images

    for field in ("ethnicity", "country", "eye_color", "hair_color", "height"):
        val = perf.get(field)
        if val:
            result[field] = val

    # birthdate: FuzzyDate { date }
    bd = perf.get("birthdate")
    if bd and bd.get("date"):
        result["birthdate"] = bd["date"]

    # measurements: Measurements { waist hip }
    ms = perf.get("measurements")
    if ms:
        parts = []
        if ms.get("waist"):
            parts.append(str(ms["waist"]))
        if ms.get("hip"):
            parts.append(str(ms["hip"]))
        if parts:
            result["measurements"] = "-".join(parts)

    # career_start_year / career_end_year
    if perf.get("career_start_year"):
        result["career_start"] = str(perf["career_start_year"])
    if perf.get("career_end_year"):
        result["career_end"] = str(perf["career_end_year"])

    logger.info("      - 👤 直连查询 %s 演员: %s | images=%d urls=%d",
                source.name, result.get("name", stash_id[:8]),
                len(images), len(urls))
    return result


# ── 单源补全：从演员 URL 交叉引用抓取其他源数据 ──────────


async def _enrich_single_source_with_crossref(
    merged: dict, sources: list, client
) -> dict:
    """当只有单源命中时，检查演员 URLs 是否有其他源的 performer ID，抓取并合并。

    参与全流程：双源 stash_ids、演员图片、别名、URLs、单值字段补全、TPDB 简介。
    """
    performers = merged.get("performers", [])
    if not performers:
        return merged

    primary = get_primary(sources)
    secondary = sources[1] if len(sources) > 1 else None
    if not secondary or not primary:
        return merged

    enriched = []
    for perf in performers:
        # 检查演员是否有双源 stash_ids
        has_dual = perf.get("stash_ids") and len(perf["stash_ids"]) > 1
        urls = perf.get("urls") or []
        other_ids = _performer_ids_from_urls(urls, secondary.domain)
        if not other_ids and has_dual:
            # 已有双源且无 URL 指向其他源 → 已完整，跳过
            enriched.append(perf)
            continue

        if not other_ids:
            enriched.append(perf)
            continue

        tp_id = list(other_ids)[0]
        logger.info(
            "      - 🔍 从 %s 演员 URL 发现 %s 演员 ID: %s",
            primary.name, secondary.name, tp_id,
        )

        other_perf = await _fetch_performer_detail(client, secondary, tp_id)
        if not other_perf:
            logger.warning("      - ⚠️ 无法获取 %s 演员数据: %s", secondary.name, tp_id)
            enriched.append(perf)
            continue

        # 全量合并（_merge_performer_pair 含 stash_ids/图片/别名/URLs/字段/TPDB 简介）
        merged_perf = await _merge_performer_pair(
            perf, other_perf, primary, secondary,
        )
        logger.info(
            "      - ✅ 跨源合并演员: %s | stash_ids=%d",
            merged_perf.get("name", "?"),
            len(merged_perf.get("stash_ids") or []),
        )
        enriched.append(merged_perf)

    if enriched:
        merged["performers"] = enriched
    return merged


async def _fetch_scene_by_url_crossref(
    scraped_primary: dict,
    primary_source: ScrapeSource,
    secondary_source: ScrapeSource,
    client,
    scene_id: str,
) -> dict | None:
    """从场景 URLs 中提取其他源的 scene ID 并补抓数据。

    检查 primary 场景的 urls 是否包含指向 secondary 源的场景链接
    （如 stashdb.org/scenes/<uuid>），提取 ID 后补抓全量数据。
    """
    scene_urls = scraped_primary.get("urls") or []
    for u in scene_urls:
        if secondary_source.domain in u and "/scenes/" in u:
            sid = u.rstrip("/").rsplit("/", 1)[-1]
            if not sid:
                continue
            logger.info(
                "   - 🔍 从场景 URL 发现 %s 场景 ID: %s",
                secondary_source.name, sid,
            )
            secondary_data = await _fetch_full(client, secondary_source, sid, scene_id)
            if secondary_data:
                logger.info(
                    "   - ✅ %s 场景 URL 交叉引用补抓成功: %s",
                    secondary_source.name, secondary_data.get("title"),
                )
                return secondary_data
    return None


# ── 统一刮削入口 ──────────────────────────────────(client, source: ScrapeSource, studio_id: str) -> dict | None:
    """直连 stash-box 查询工作室的 parent 关系。"""
    key = _get_stashbox_key(client, source.endpoint)
    if not key:
        return None
    query = """
    query($id: ID!) {
      findStudio(id: $id) { name parent { name } }
    }
    """
    try:
        r = httpx.post(
            source.endpoint,
            json={"query": query, "variables": {"id": studio_id}},
            timeout=30,
            proxy=STASHBOX_PROXY,
            verify=False,
            headers={"ApiKey": key},
        )
        data = r.json()
    except Exception as e:
        logger.warning("      - ⚠️ 查询工作室 parent 异常: %s", e)
        return None
    if "errors" in data:
        return None
    studio = data.get("data", {}).get("findStudio")
    if studio and studio.get("parent"):
        parent = studio["parent"]
        return {"name": parent["name"]}
    return None


async def _fetch_studio_detail(client, source: ScrapeSource, studio_id: str) -> dict | None:
    """直连 stash-box 查询工作室详情（image/urls/parent，因 9999 ScrapedSceneStudio 不返回这些）。"""
    key = _get_stashbox_key(client, source.endpoint)
    if not key:
        return None
    query = """
    query($id: ID!) {
      findStudio(id: $id) {
        id name urls { url }
        images { id url }
        parent { id name }
      }
    }
    """
    try:
        r = httpx.post(
            source.endpoint,
            json={"query": query, "variables": {"id": studio_id}},
            timeout=30,
            proxy=STASHBOX_PROXY,
            verify=False,
            headers={"ApiKey": key},
        )
        data = r.json()
    except Exception as e:
        logger.warning("      - ⚠️ 查询工作室详情异常: %s", e)
        return None
    if "errors" in data:
        logger.warning("      - ⚠️ 查询工作室详情错误: %s", data["errors"])
        return None
    studio = data.get("data", {}).get("findStudio")
    if not studio:
        return None
    result = {}
    urls = [u["url"] for u in (studio.get("urls") or []) if u.get("url")]
    if urls:
        result["urls"] = urls
    imgs = studio.get("images") or []
    if imgs and imgs[0].get("url"):
        result["image_url"] = imgs[0]["url"]
    parent = studio.get("parent")
    if parent and parent.get("name"):
        result["parent"] = {"name": parent["name"]}
    return result


# ── 统一刮削入口 ──────────────────────────────────


async def scrape_scene_auto(
    client,
    scene_id: str,
    scene_type: str = "NONJAV",
) -> dict | None:
    """统一刮削入口：指纹直连 → 9999 拉全量 → 多源合并。

    Args:
        client: StashClient
        scene_id: 本地场景 ID
        scene_type: 'JAV' | 'NONJAV'

    Returns:
        合并后的 ScrapedScene dict，失败返回 None。
    """
    logger.info("   - 🚀 统一刮削 | 场景=%s | 类型=%s", scene_id, scene_type)

    if scene_type == "JAV":
        from scrape.sources import JAV_SOURCES
        # JAV 暂不通过 box（保留原有 stashbox + 插件体系）
        logger.warning("   - ⏭️ JAV 使用原有流程")
        return None

    # 1. 确保配置缓存
    await _ensure_config_cache(client)

    # 2. 取指纹
    fprints = await _get_scene_fingerprints(client, scene_id)
    if not fprints:
        logger.warning("   - ⚠️ 场景 %s 无指纹，跳过", scene_id)
        return None
    logger.info("   - 🔑 指纹: oshash=%s phash=%s",
                fprints.get("oshash", "")[:12],
                fprints.get("phash", "")[:12])

    sources = NONJAV_SOURCES
    primary = get_primary(sources)
    secondary = sources[1] if len(sources) > 1 else None

    # 3. 指纹查库（逐源）
    stash_ids = {}
    for src in sources:
        if not src.fingerprint_supported:
            continue
        sid = await _fingerprint_search(src, fprints, client)
        if sid:
            stash_ids[src.name] = sid
            logger.info("   - ✅ %s 命中: %s", src.name, sid)

    if not stash_ids:
        logger.warning("   - ⚠️ 所有站点指纹均未命中，跳过")
        return None

    # 4. 用 stash_ids 从 9999 拉全量
    scraped_data = {}
    for src in sources:
        sid = stash_ids.get(src.name)
        if not sid:
            continue
        data = await _fetch_full(client, src, sid, scene_id)
        if data:
            scraped_data[src.name] = data
            logger.info("   - ✅ %s 全量拉取成功: %s", src.name, data.get("title"))

    # 5. 多源合并
    scraped_primary = scraped_data.get(primary.name) if primary else None
    scraped_secondary = scraped_data.get(secondary.name) if secondary else None

    # 5a. 单源场景 URL 交叉引用：从场景 URLs 提取其他源 scene ID 补抓并重新合并
    if not scraped_secondary and scraped_primary and secondary:
        scraped_secondary = await _fetch_scene_by_url_crossref(
            scraped_primary, primary, secondary, client, scene_id,
        )
        if scraped_secondary:
            scraped_data[secondary.name] = scraped_secondary

    merged = await _merge_scraped(
        scraped_primary, scraped_secondary,
        primary, secondary,
        scene_id, client,
    )

    if not merged:
        logger.warning("   - ⚠️ 合并后无数据")
        return None

    # 6. 单源补全：从演员 URL 交叉引用抓取其他源数据（封面/演员/标签/URL 全流程参与）
    if not scraped_secondary:
        merged = await _enrich_single_source_with_crossref(merged, sources, client)

    merged["_source"] = scene_type
    logger.info("   - ✅ 合并完成: %s | 演员=%d 标签=%d urls=%d",
                merged.get("title"),
                len(merged.get("performers") or []),
                len(merged.get("tags") or []),
                len(merged.get("urls") or []))
    return merged