"""标记同步核心工具函数（从 stash-marker-sync 移植，异步版）。

功能：标记对比/新建/更新/跳过、标签对照、url 增量、stash_id 增量、
      tt movies → Group、TPDB movies → Group（补充 image/back_image）。

设计：统一使用 stash/scene.py 的公共 API，不依赖 stash-marker-sync 的私有客户端。
"""
import logging
import re
from urllib.parse import urlparse

from stash import scene as scene_mod
from stash import tag as tag_mod

logger = logging.getLogger(__name__)

TT_SCENE_PREFIX = "https://timestamp.trade/scene/"
TT_MOVIE_URL = "https://timestamp.trade/movie/%s"
TPDB_ENDPOINT = "https://theporndb.net/graphql"


def _norm(name: str) -> str:
    """规范化标签名：多个空格压成单空格，strip。"""
    if not name:
        return ""
    return re.sub(r"\s+", " ", name).strip()


def _domain(endpoint: str) -> str:
    """提取 endpoint 的域名（忽略 scheme/port/query）。"""
    try:
        return urlparse(endpoint).hostname or endpoint
    except Exception:
        return endpoint


def _extract_tpdb_studio_name(site_field):
    """从 TPDB movie 的 site 字段提取工作室名称。site 可能是字符串或 {name: ...} 对象。"""
    if not site_field:
        return None
    if isinstance(site_field, str):
        return site_field
    if isinstance(site_field, dict):
        return site_field.get("name") or None
    return None


def _tt_stash_ids(tt_scene: dict) -> list:
    """tt json-scene 里的 stash_id 列表。"""
    out = []
    raw = tt_scene.get("stashid")
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        ep = item.get("endpoint") or ""
        sid = item.get("stashid") or item.get("stash_id") or ""
        if sid.startswith("http"):
            sid = sid.rstrip("/").rsplit("/", 1)[-1]
        if ep and sid:
            out.append({"endpoint": ep, "stash_id": sid})
    return out


# ── 标记同步 ──

async def _primary_tag_id(client, tag_name):
    """按名字反查标签 → 查到用 id / 查不到创建。返回 (tag_id, created)。"""
    if not tag_name:
        return None, False
    tag_name = _norm(tag_name)
    tag = await tag_mod.get_tag_with_aliases(client, tag_name)
    if tag:
        return tag["id"], False
    tid = await tag_mod.create_or_find_tag(client, tag_name, verbose=False)
    if tid:
        return tid, True
    return None, False


async def sync_markers(client, scene, ext_markers, source,
                        add_tag=False, add_title=False, source_tag="", source_prefix="",
                        skip_existing=False):
    """外部标记 → 本地 scene_markers 同步（跳过/更新/新建）。返回标记是否有变更。

    ext_markers 支持两种格式：
      tt:   { name, start_time(毫秒), tag_name }
      TPDB: { title, start_time(秒) }
    """
    changed = False
    local = scene.get("scene_markers") or []
    logger.info("      - 📍 标记 %s: 外部 %d 个, 本地 %d 个%s%s",
                source, len(ext_markers), len(local),
                f" [加{source_tag}标签]" if add_tag else "",
                f" [加{source_prefix.strip()}前缀]" if add_title else "")

    # 归一化
    norm = []
    for m in ext_markers:
        if "name" in m:  # tt 格式（毫秒）
            seconds = int((m.get("start_time") or 0) / 1000)
            title = m.get("name") or ""
            tag_name = m.get("tag_name") or title
        else:  # TPDB 格式（秒）
            seconds = int(m.get("start_time") or 0)
            title = m.get("title") or ""
            tag_name = title
        if not title:
            continue
        if add_title:
            title = f"{source_prefix}{title}"
        extra_tag_ids = []
        if add_tag:
            tag = await tag_mod.get_tag_with_aliases(client, source_tag)
            if tag:
                extra_tag_ids.append(tag["id"])
        norm.append({"seconds": seconds, "title": title, "tag_name": tag_name,
                     "extra_tag_ids": extra_tag_ids})

    # 去重
    seen = set()
    dedup = []
    for nm in norm:
        key = (nm["seconds"], nm["title"], nm["tag_name"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(nm)
    if len(dedup) != len(norm):
        logger.info("      - ↺ %s markers 去重: %d → %d", source, len(norm), len(dedup))
    norm = dedup

    local_by_sec = {}
    for m in local:
        local_by_sec.setdefault(m["seconds"], []).append(m)

    scene_id = scene.get("id")
    for nm in norm:
        seconds = nm["seconds"]
        title = nm["title"]
        tag_name = nm["tag_name"]

        tag_id, created = await _primary_tag_id(client, tag_name)
        if not tag_id:
            logger.debug("跳过标记 %s: 无主标签", title)
            continue

        candidates = local_by_sec.get(seconds, [])
        if not candidates:
            changed = True
            logger.info("      - %s %ds 新建标记 %r (主标签 %s)%s",
                        "✅" if True else "🔍", seconds, title, tag_name,
                        f" 附加标签 {nm['extra_tag_ids']}" if nm["extra_tag_ids"] else "")
            await scene_mod.create_scene_marker(
                client, scene_id, seconds, tag_id, title,
                nm["extra_tag_ids"] or None,
            )
            continue

        if skip_existing:
            logger.info("      - ⏭️  %ds 时间点已存在标记，%s 跳过（补缺模式）", seconds, source)
            continue

        matched = None
        for c in candidates:
            c_tag = c.get("primary_tag") or {}
            same_title = (c.get("title") or "") == title
            same_tag = (c_tag.get("id") or "") == str(tag_id) or (c_tag.get("name") or "") == tag_name
            if same_title and same_tag:
                matched = c
                break
        if matched:
            logger.info("      - ⏭️  %ds 已存在相同标记 %r，跳过", seconds, title)
            continue

        target = candidates[0]
        changed = True
        logger.info("      - %s %ds 覆盖更新标记 %r → %r (主标签 %s)%s",
                    "✅" if True else "🔍", seconds, target.get("title"), title, tag_name,
                    f" 附加标签 {nm['extra_tag_ids']}" if nm["extra_tag_ids"] else "")
        await scene_mod.update_scene_marker(
            client, target["id"], seconds, tag_id, title,
            nm["extra_tag_ids"] or None,
        )

    return changed


# ── tt 标签对照 ──

async def sync_tags(client, scene, tt_scene):
    """tt tags → 本地场景标签对照：名称和别名都没有 → 创建并关联。"""
    tt_tags = tt_scene.get("tags") or []
    local_tags = scene.get("tags") or []
    if not tt_tags:
        return
    logger.info("      - 🏷️  tt 标签 %d 个, 本地场景标签 %d 个", len(tt_tags), len(local_tags))

    local_names = set()
    local_aliases = set()
    for t in local_tags:
        local_names.add(_norm(t.get("name") or "").lower())
        for a in t.get("aliases") or []:
            local_aliases.add(_norm(a).lower())

    to_add = []
    for t in tt_tags:
        name = t.get("name") or t
        if isinstance(t, str):
            name = t
        name = _norm(name)
        if not name:
            continue
        low = name.lower()
        if low in local_names or low in local_aliases:
            continue
        tid = await tag_mod.create_or_find_tag(client, name, verbose=False)
        if tid:
            to_add.append(tid)
            logger.info("      - ✅ [tag_create] 创建并关联标签 %s", name)

    if to_add:
        new_ids = [t["id"] for t in local_tags] + to_add
        await scene_mod.update_scene(client, {"id": scene["id"], "tag_ids": new_ids})


# ── url 增量 ──

async def sync_urls(client, scene, tt_scene):
    """tt urls → 本地场景 urls 增量添加。"""
    tt_urls = tt_scene.get("urls") or []
    if isinstance(tt_urls, list) and tt_urls and isinstance(tt_urls[0], dict):
        tt_urls = [u.get("url") for u in tt_urls if u.get("url")]
    local = scene.get("urls") or []
    if not tt_urls:
        return
    logger.info("      - 🔗 url: tt %d 个, 本地 %d 个", len(tt_urls), len(local))
    local_set = set(local)
    new = [u for u in tt_urls if u not in local_set]
    if new:
        logger.info("      - ✅ [url] 追加 urls +%d 个 (%s)", len(new), new)
        await scene_mod.update_scene(client, {"id": scene["id"], "urls": local + new})


# ── stash_id 增量 ──

async def sync_stash_ids(client, scene, tt_scene):
    """tt stash_id → 对照本地配置的 stash-box 实例做域名匹配 → 场景缺失的补上。"""
    tt_sids = _tt_stash_ids(tt_scene)
    if not tt_sids:
        return
    # 从 Stash 配置拿实例列表
    data = await client.post("""
        query {
          configuration { general { stashBoxes { name endpoint } } }
        }
    """, {})
    if not data:
        return
    boxes = data.get("configuration", {}).get("general", {}).get("stashBoxes") or []
    logger.info("      - 🆔 stash_id: tt %d 个, 本地配置实例 %d 个", len(tt_sids), len(boxes))

    box_domains = {}
    for b in boxes:
        d = _domain(b.get("endpoint") or "")
        if d:
            box_domains.setdefault(d, []).append(b["endpoint"])

    local_sids = scene.get("stash_ids") or []
    local_endpoints = set(x.get("endpoint") or "" for x in local_sids)

    added = []
    for sid in tt_sids:
        ep = sid.get("endpoint") or ""
        d = _domain(ep)
        if d not in box_domains:
            logger.info("      - ⏭️  %s 不在本地配置实例中，跳过", ep)
            continue
        matched_local_eps = box_domains[d]
        if any(x in local_endpoints for x in matched_local_eps):
            logger.info("      - ⏭️  场景已有 %s 的 stash_id", ep)
            continue
        logger.info("      - ✅ [stash_id] 补 stash_id %s → %s", ep, sid.get("stash_id"))
        await scene_mod.update_scene(
            client, scene["id"],
            stash_ids=local_sids + [sid],
        )
        added.append(sid)

    if added:
        logger.info("      - ➕ 将补 %d 个 stash_id", len(added))


# ── 集合（Group）同步：tt movies → Group ──

async def sync_groups(client, scene, tt_scene):
    """同步 tt movies → 本地 Stash Group。"""
    movies = tt_scene.get("movies") or []
    if not movies:
        logger.info("      - ℹ️  [tt] 无集合（movies）数据，跳过")
        return

    scene_id = scene.get("id")
    current_group_ids = set()
    current_index = {}
    for g in (scene.get("groups") or []):
        grp = g.get("group") or {}
        gid = grp.get("id")
        if gid:
            current_group_ids.add(gid)
            current_index[gid] = g.get("scene_index")

    tt_scene_id = tt_scene.get("scene_id")
    new_groups = []
    created_group_ids = []

    for m in movies:
        mtitle = m.get("title")
        if not mtitle:
            continue
        in_this_scene = False
        scene_index = None
        for sc in (m.get("scenes") or []):
            if sc.get("scene_id") == tt_scene_id:
                in_this_scene = True
                scene_index = sc.get("scene_index")
                break
        if not in_this_scene:
            continue

        tt_url = TT_MOVIE_URL % m.get("id")
        gid = await scene_mod.find_group_by_url(client, tt_url, name=mtitle)
        if gid:
            await _update_group_fields(client, gid, m)
        else:
            gid = await _create_group_from_tt(client, m)
            if gid:
                created_group_ids.append(gid)

        if gid:
            old_idx = current_index.get(gid)
            if scene_index is not None and old_idx != scene_index:
                logger.info("      - [group_index] 集合 %s scene_index: %s -> %s", mtitle, old_idx, scene_index)
            new_groups.append({"group_id": gid, "scene_index": scene_index})

    if new_groups:
        merged = []
        seen = set()
        for g in new_groups:
            merged.append(g)
            seen.add(g["group_id"])
        for gid in current_group_ids:
            if gid not in seen:
                merged.append({"group_id": gid, "scene_index": current_index.get(gid)})
        logger.info("      - ✅ [group] 场景关联集合 %d 个（含新建 %d）", len(new_groups), len(created_group_ids))
        await scene_mod.update_scene(client, {"id": scene_id, "groups": merged})
    else:
        logger.info("      - ℹ️  [tt] 场景不属于任何 movies（集合）")


async def _create_group_from_tt(client, m: dict):
    """按 tt movie 数据创建 Group。"""
    inp = {"name": m.get("title") or ""}
    if not inp["name"]:
        return None
    if m.get("description"):
        inp["synopsis"] = m["description"]
    if m.get("director"):
        inp["director"] = m["director"]
    if m.get("release_date"):
        inp["date"] = m["release_date"]
    inp["urls"] = [TT_MOVIE_URL % m.get("id")]
    studio_name = m.get("studio_name")
    if studio_name:
        sid = await scene_mod.find_or_create_studio_by_name(client, studio_name)
        if sid:
            inp["studio_id"] = sid
    gid = await scene_mod.create_group(client, inp)
    if gid:
        logger.info("      - ✅ [group_create] 创建集合: %s (id %s)", inp["name"], gid)
    return gid


async def _update_group_fields(client, group_id: str, m: dict):
    """更新已有 Group 的缺失字段（synopsis/director/date 补缺）。"""
    cur = await scene_mod.find_group(client, group_id)
    if not cur:
        return
    inp = {"id": group_id}
    changed = False
    if not cur.get("synopsis") and m.get("description"):
        inp["synopsis"] = m["description"]
        changed = True
    if not cur.get("director") and m.get("director"):
        inp["director"] = m["director"]
        changed = True
    if not cur.get("date") and m.get("release_date"):
        inp["date"] = m["release_date"]
        changed = True
    tt_url = TT_MOVIE_URL % m.get("id")
    if tt_url not in (cur.get("urls") or []):
        inp["urls"] = (cur.get("urls") or []) + [tt_url]
        changed = True
    if changed:
        await scene_mod.update_group(client, inp)
        logger.info("      - ✅ [group_update] 更新集合: %s", cur.get("name"))


# ── 集合（Group）同步：TPDB movies → Group（补充 tt 缺失的字段）──

async def sync_groups_tpdb(client, scene, tpdb_scene):
    """同步 TPDB movies → 本地 Stash Group（补充 tt 源未覆盖的字段）。

    TPDB movies 比 tt movies 多的字段：image/back_image/url(工作室网站链接) 等。
    如果 Group 已存在（tt 源创建的），只补缺 TPDB 特有字段；
    不存在则用 TPDB 全量数据创建（含 front_image/back_image）。
    """
    movies = tpdb_scene.get("movies") or []
    if not movies:
        logger.info("      - ℹ️  [TPDB] 无集合（movies）数据，跳过")
        return

    scene_id = scene.get("id")
    current_group_ids = set()
    current_index = {}
    for g in (scene.get("groups") or []):
        grp = g.get("group") or {}
        gid = grp.get("id")
        if gid:
            current_group_ids.add(gid)
            current_index[gid] = g.get("scene_index")

    new_groups = []
    created_group_ids = []

    for m in movies:
        mtitle = m.get("title")
        if not mtitle:
            continue

        tpdb_url = m.get("url") or ""
        gid = await scene_mod.find_group_by_url(client, tpdb_url, name=mtitle) if tpdb_url else \
              await scene_mod.find_group_by_url(client, "", name=mtitle)
        if not gid and tpdb_url:
            gid = await scene_mod.find_group_by_url(client, "", name=mtitle)

        if gid:
            await _update_group_fields_tpdb(client, gid, m)
        else:
            gid = await _create_group_from_tpdb(client, m)
            if gid:
                created_group_ids.append(gid)

        if gid:
            new_groups.append({"group_id": gid, "scene_index": None})

    if new_groups:
        merged = []
        seen = set()
        for g in new_groups:
            merged.append(g)
            seen.add(g["group_id"])
        for gid in current_group_ids:
            if gid not in seen:
                merged.append({"group_id": gid, "scene_index": current_index.get(gid)})
        logger.info("      - ✅ [TPDB] 场景关联集合 %d 个（含新建 %d）", len(new_groups), len(created_group_ids))
        await scene_mod.update_scene(client, {"id": scene_id, "groups": merged})
    else:
        logger.info("      - ℹ️  [TPDB] 场景不属于任何 movies（集合）")


async def _create_group_from_tpdb(client, m: dict):
    """按 TPDB movie 数据创建 Group（比 tt 多 image/back_image 等字段）。"""
    inp = {"name": m.get("title") or ""}
    if not inp["name"]:
        return None
    if m.get("description"):
        inp["synopsis"] = m["description"]
    if m.get("date"):
        inp["date"] = m["date"]
    if m.get("url"):
        inp["urls"] = [m["url"]]
    if m.get("image"):
        inp["front_image"] = m["image"]
    if m.get("back_image"):
        inp["back_image"] = m["back_image"]
    site_name = _extract_tpdb_studio_name(m.get("site"))
    if site_name:
        sid = await scene_mod.find_or_create_studio_by_name(client, site_name)
        if sid:
            inp["studio_id"] = sid
    gid = await scene_mod.create_group(client, inp)
    if gid:
        detail = inp["name"]
        if m.get("image"):
            detail += " +front_image"
        if m.get("back_image"):
            detail += " +back_image"
        logger.info("      - ✅ [TPDB:group_create] 创建集合: %s (id %s)", detail, gid)
    return gid


async def _update_group_fields_tpdb(client, group_id: str, m: dict):
    """更新已有 Group 的 TPDB 特有字段（image/back_image/url 等补缺，已有不覆盖）。"""
    cur = await scene_mod.find_group(client, group_id)
    if not cur:
        return
    inp = {"id": group_id}
    changed = False

    if not cur.get("front_image_path") and m.get("image"):
        inp["front_image"] = m["image"]
        changed = True
    if not cur.get("back_image_path") and m.get("back_image"):
        inp["back_image"] = m["back_image"]
        changed = True
    tpdb_url = m.get("url") or ""
    if tpdb_url and tpdb_url not in (cur.get("urls") or []):
        inp["urls"] = (cur.get("urls") or []) + [tpdb_url]
        changed = True
    if not cur.get("synopsis") and m.get("description"):
        inp["synopsis"] = m["description"]
        changed = True
    if not cur.get("director") and m.get("director"):
        inp["director"] = m["director"]
        changed = True
    if not cur.get("date") and m.get("date"):
        inp["date"] = m["date"]
        changed = True

    if changed:
        await scene_mod.update_group(client, inp)
        logger.info("      - ✅ [TPDB:group_update] 更新集合: %s (补缺)", cur.get("name"))
    else:
        logger.info("      - ⏭️  [TPDB] 集合 %s 已是最新，无需更新", cur.get("name"))