"""片商操作：查找、创建、更新。"""

import logging

from stash import query as Q

logger = logging.getLogger(__name__)

_STUDIO_FULL_QUERY = """
query FindStudioFull($id: ID!) {
  findStudio(id: $id) {
    id name url urls details aliases
    parent_studio { id name }
    stash_ids { endpoint stash_id }
  }
}
"""


async def find_studio_by_name(client, studio_name):
    """根据名称查找工作室。返回 id 或 None。"""
    data = await client.post(
        Q.FIND_STUDIOS,
        {
            "filter": {"q": studio_name, "per_page": 1},
            "studio_filter": {
                "name": {"value": studio_name, "modifier": "EQUALS"}
            },
        },
    )
    if data and data.get("findStudios", {}).get("count", 0) > 0:
        return data["findStudios"]["studios"][0]["id"]
    return None


async def find_studio_by_stash_id(client, endpoint, stash_id):
    """按 stash_id 查找工作室。返回 id 或 None。"""
    data = await client.post(Q.FIND_STUDIOS, {
        "filter": {"per_page": -1},
    })
    if not data:
        return None
    studios = data.get("findStudios", {}).get("studios", [])
    for s in studios:
        for sid in (s.get("stash_ids") or []):
            if sid.get("endpoint") == endpoint and sid.get("stash_id") == stash_id:
                return s["id"]
    return None


async def get_studio_full(client, studio_id):
    """获取工作室完整信息（含 stash_ids/parent）。"""
    data = await client.post(_STUDIO_FULL_QUERY, {"id": str(studio_id)})
    if not data:
        return None
    return data.get("findStudio")


async def create_or_find_studio(client, studio_data, stash_box_index=0):
    """查找或创建工作室（含父工作室递归创建）。返回 studio_id 或 None。

    优先按 stash_ids（多源）匹配，其次名称。
    已存在 → 更新检测补齐（stash_ids/urls/image/parent）。
    """
    name = studio_data.get("name")
    if not name:
        return None

    # ── 1. 按 stash_id 匹配（多源） ──
    stash_ids = studio_data.get("stash_ids") or []
    if not stash_ids and studio_data.get("remote_site_id"):
        endpoint_url = await client.get_endpoint(stash_box_index)
        stash_ids = [{"endpoint": endpoint_url, "stash_id": studio_data["remote_site_id"]}]

    existing_id = None
    for sid in stash_ids:
        if not sid.get("endpoint") or not sid.get("stash_id"):
            continue
        existing_id = await find_studio_by_stash_id(client, sid["endpoint"], sid["stash_id"])
        if existing_id:
            break

    if not existing_id:
        existing_id = await find_studio_by_name(client, name)

    # ── 2. 已有 → 更新检测 ──
    if existing_id:
        await update_studio_full(client, existing_id, studio_data, stash_box_index)
        return existing_id

    # ── 3. 新建 ──
    inp = {"name": name}
    if studio_data.get("url"):
        inp["url"] = studio_data["url"]
    urls = studio_data.get("urls")
    if urls:
        inp["urls"] = urls
    if studio_data.get("details"):
        inp["details"] = studio_data["details"]
    if studio_data.get("image"):
        inp["image"] = studio_data["image"]
    if studio_data.get("aliases"):
        inp["aliases"] = studio_data["aliases"]
    if stash_ids:
        inp["stash_ids"] = stash_ids

    # 递归创建父工作室
    parent = studio_data.get("parent")
    if parent and parent.get("name"):
        parent_id = await create_or_find_studio(client, parent, stash_box_index)
        if parent_id:
            inp["parent_id"] = parent_id
            logger.info("         - 🏢 父工作室: %s", parent["name"])

    inp = {k: v for k, v in inp.items() if v is not None and v != [] and v != {} and v != ""}

    data = await client.post(Q.STUDIO_CREATE, {"input": inp})
    if data and data.get("studioCreate"):
        sid = data["studioCreate"]["id"]
        logger.info("         - 🏢 创建新工作室: %s", name)
        return sid

    logger.warning("         - ⚠️ 创建工作室失败: %s", name)
    return None


async def update_studio_full(client, studio_id, studio_data, stash_box_index=0):
    """更新已有工作室的缺失字段（全字段 diff，已有的不覆盖）。"""
    existing = await get_studio_full(client, studio_id)
    if not existing:
        return False

    inp = {"id": str(studio_id)}
    changed = False

    # stash_ids：new 权威覆盖同 endpoint（含清除同 endpoint 多值脏数据），保留 new 没有的 endpoint
    new_stash_ids = studio_data.get("stash_ids") or []
    if not new_stash_ids and studio_data.get("remote_site_id"):
        endpoint_url = await client.get_endpoint(stash_box_index)
        new_stash_ids = [{"endpoint": endpoint_url, "stash_id": studio_data["remote_site_id"]}]
    if new_stash_ids:
        new_by_ep = {sid.get("endpoint"): sid.get("stash_id") for sid in new_stash_ids if sid.get("endpoint")}
        old_ids = existing.get("stash_ids") or []
        old_counts = {}
        old_by_ep = {}
        for s in old_ids:
            ep = s.get("endpoint")
            if not ep:
                continue
            old_counts[ep] = old_counts.get(ep, 0) + 1
            old_by_ep[ep] = s.get("stash_id")
        merged_map = {}
        for ep, sid in old_by_ep.items():
            if ep not in new_by_ep:
                merged_map[ep] = sid
        for ep, sid in new_by_ep.items():
            merged_map[ep] = sid
            if old_counts.get(ep, 0) != 1 or old_by_ep.get(ep) != sid:
                changed = True
        if changed:
            inp["stash_ids"] = [{"endpoint": ep, "stash_id": sid} for ep, sid in merged_map.items()]

    # 父工作室：缺失才补
    existing_parent = existing.get("parent_studio")
    if not existing_parent:
        parent = studio_data.get("parent")
        if parent and parent.get("name"):
            parent_id = await create_or_find_studio(client, parent, stash_box_index)
            if parent_id:
                inp["parent_id"] = parent_id
                changed = True

    # urls：合并缺失
    new_urls = studio_data.get("urls") or []
    if studio_data.get("url"):
        new_urls.append(studio_data["url"])
    if new_urls:
        curr_urls = {u for u in (existing.get("urls") or [])}
        if existing.get("url"):
            curr_urls.add(existing["url"])
        merged_urls = list(existing.get("urls") or [])
        if existing.get("url") and existing["url"] not in merged_urls:
            merged_urls.insert(0, existing["url"])
        for u in new_urls:
            if u not in curr_urls:
                merged_urls.append(u)
                curr_urls.add(u)
                changed = True
        if merged_urls:
            inp["urls"] = merged_urls

    # 单值字段：缺失才补
    for field in ("details", "image", "aliases"):
        if not existing.get(field) and studio_data.get(field):
            inp[field] = studio_data[field]
            changed = True

    if not changed:
        return False

    inp = {k: v for k, v in inp.items() if v is not None and v != [] and v != {} and v != ""}
    data = await client.post(Q.STUDIO_UPDATE, {"input": inp})
    if data and data.get("studioUpdate"):
        logger.info("         - 🏢 更新工作室字段 %s (%d 项)", existing.get("name"), sum(1 for _ in inp) - 1)
        return True
    logger.warning("         - ⚠️ 工作室更新失败: %s", existing.get("name"))
    return False


def compare_studio(current_studio, scraped_studio):
    """比较当前工作室和刮削工作室。返回 (need_update, reason, studio_id)。"""
    current = current_studio or {}
    scraped = scraped_studio or {}
    if scraped.get("stored_id") or scraped.get("name"):
        if not current.get("id"):
            return True, "当前无工作室，添加", scraped
        if current.get("name") != scraped.get("name"):
            return True, "工作室名称不同: %s -> %s" % (current.get("name"), scraped.get("name")), scraped
    return False, "工作室无变化", None