"""演员操作：查找、创建、更新。"""

import logging

from stash import query as Q

logger = logging.getLogger(__name__)

_PERFORMER_QUERY = """
query FindPerformerFull($id: ID!) {
  findPerformer(id: $id) {
    id name gender birthdate country measurements
    disambiguation ethnicity eye_color hair_color fake_tits
    career_start career_end tattoos piercings
    height_cm weight
    alias_list urls image_path stash_ids { endpoint stash_id }
  }
}
"""


async def find_performer_by_name(client, performer_name):
    """按名称（含别名）查找演员。返回 performer dict 或 None。"""
    data = await client.post(Q.FIND_PERFORMERS, {
        "filter": {"per_page": -1}
    })
    if not data:
        return None
    performers = data.get("findPerformers", {}).get("performers", [])
    target_lower = performer_name.lower()
    for p in performers:
        if p.get("name", "").lower() == target_lower:
            return p
        # 检查别名列表
        aliases = p.get("alias_list") or []
        if any(a.lower() == target_lower for a in aliases):
            return p
    return None


async def find_performer_by_stash_id(client, endpoint, stash_id):
    """按 stash_id 查找演员。返回 performer dict 或 None。"""
    data = await client.post(Q.FIND_PERFORMERS, {
        "filter": {"per_page": -1},
    })
    if not data:
        return None
    performers = data.get("findPerformers", {}).get("performers", [])
    for p in performers:
        for sid in (p.get("stash_ids") or []):
            if sid.get("endpoint") == endpoint and sid.get("stash_id") == stash_id:
                return p
    return None


async def get_performer_full(client, performer_id):
    """获取演员完整信息（含 stash_ids）。"""
    data = await client.post(_PERFORMER_QUERY, {"id": str(performer_id)})
    if not data:
        return None
    return data.get("findPerformer")


async def create_or_find_performer(client, performer_data, stash_box_index=0):
    """创建或查找演员，返回 performer_id 或 None。

    优先按 stash_ids（多源）匹配；没有则按名称。
    已存在的演员：检查是否有新字段（全字段更新），有则补齐。
    """
    name = performer_data.get("name", "")
    if not name:
        return None

    # ── 1. 按 stash_id 匹配（多源） ──
    stash_ids = performer_data.get("stash_ids") or []
    if not stash_ids and performer_data.get("remote_site_id"):
        endpoint_url = await client.get_endpoint(stash_box_index)
        stash_ids = [{"endpoint": endpoint_url, "stash_id": performer_data["remote_site_id"]}]

    existing = None
    for sid in stash_ids:
        if not sid.get("endpoint") or not sid.get("stash_id"):
            continue
        existing = await find_performer_by_stash_id(
            client, sid["endpoint"], sid["stash_id"]
        )
        if existing:
            break

    # ── 2. 按名称匹配 ──
    if not existing:
        existing = await find_performer_by_name(client, name)

    # ── 3. 已有 → 更新检测（全字段补齐，已有的不覆盖） ──
    if existing:
        pid = existing["id"]
        await update_performer_full(client, pid, performer_data, stash_box_index)
        return pid

    # ── 4. 新建 ──
    input_data = {"name": name}
    for field in ("gender", "birthdate", "country", "measurements"):
        val = performer_data.get(field)
        if val:
            input_data[field] = val

    for field in ("disambiguation", "ethnicity", "eye_color", "hair_color",
                   "fake_tits", "career_start", "career_end", "tattoos", "piercings"):
        val = performer_data.get(field)
        if val:
            input_data[field] = val

    height_val = performer_data.get("height")
    if height_val:
        try:
            input_data["height_cm"] = int(height_val)
        except (ValueError, TypeError):
            pass

    raw_aliases = performer_data.get("aliases")
    if isinstance(raw_aliases, str):
        aliases = [a.strip() for a in raw_aliases.split(",") if a.strip()]
    elif isinstance(raw_aliases, list):
        aliases = raw_aliases
    else:
        aliases = []
    if aliases:
        input_data["alias_list"] = aliases

    urls = performer_data.get("urls")
    if urls:
        input_data["urls"] = urls

    images = performer_data.get("images") or []
    if images:
        input_data["image"] = images[0]

    if stash_ids:
        input_data["stash_ids"] = stash_ids

    input_data = {k: v for k, v in input_data.items() if v is not None and v != []}

    data = await client.post(Q.PERFORMER_CREATE, {"input": input_data})
    if data and data.get("performerCreate"):
        pid = data["performerCreate"]["id"]
        logger.info("         - 👤 创建新演员: %s", name)
        return pid
    logger.warning("         - ⚠️ 演员创建失败: %s", name)
    return None


async def update_performer_full(client, performer_id, performer_data, stash_box_index=0):
    """更新已有演员的缺失字段（全字段 diff，已有的不覆盖）。"""
    existing = await get_performer_full(client, performer_id)
    if not existing:
        return False

    inp = {"id": str(performer_id)}
    changed = False

    # stash_ids：new 权威覆盖同 endpoint（含清除同 endpoint 多值脏数据），保留 new 没有的 endpoint
    new_stash_ids = performer_data.get("stash_ids") or []
    if not new_stash_ids and performer_data.get("remote_site_id"):
        endpoint_url = await client.get_endpoint(stash_box_index)
        new_stash_ids = [{"endpoint": endpoint_url, "stash_id": performer_data["remote_site_id"]}]
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
        # 构建最终 map：new 覆盖同 endpoint（清掉全部旧值），保留 new 没有的 endpoint
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

    # 单值字段：缺失才补
    for field, src_field in (
        ("gender", "gender"),
        ("birthdate", "birthdate"),
        ("country", "country"),
        ("measurements", "measurements"),
        ("ethnicity", "ethnicity"),
        ("eye_color", "eye_color"),
        ("hair_color", "hair_color"),
        ("fake_tits", "fake_tits"),
        ("career_start", "career_start"),
        ("career_end", "career_end"),
        ("tattoos", "tattoos"),
        ("piercings", "piercings"),
        ("disambiguation", "disambiguation"),
        ("details", "details"),
    ):
        if not existing.get(field) and performer_data.get(src_field):
            inp[field] = performer_data[src_field]
            changed = True

    # height_cm
    if not existing.get("height_cm") and performer_data.get("height"):
        try:
            inp["height_cm"] = int(performer_data["height"])
            changed = True
        except (ValueError, TypeError):
            pass

    # 别名：new 权威合并（⚠️ 2026-08-18 暂不清理旧别名——单字符过滤可能误删用户手动添加的别名）
    new_aliases = performer_data.get("aliases")
    if isinstance(new_aliases, str):
        new_aliases = [a.strip() for a in new_aliases.split(",") if a.strip()]
    elif not isinstance(new_aliases, list):
        new_aliases = []
    # 旧别名保留原样（不清理单字符——可能是用户手动加的）
    # old_aliases = [a for a in (existing.get("alias_list") or []) if len(a.strip()) > 1]
    old_aliases = list(existing.get("alias_list") or [])
    curr_aliases = {a.lower() for a in old_aliases}
    merged_aliases = list(old_aliases)
    if new_aliases:
        for a in new_aliases:
            if a.lower() not in curr_aliases:
                merged_aliases.append(a)
                curr_aliases.add(a.lower())
                changed = True
    if merged_aliases:
        inp["alias_list"] = merged_aliases

    # urls：合并缺失
    new_urls = performer_data.get("urls") or []
    if new_urls:
        curr_urls = {u for u in (existing.get("urls") or [])}
        merged_urls = list(existing.get("urls") or [])
        for u in new_urls:
            if u not in curr_urls:
                merged_urls.append(u)
                curr_urls.add(u)
                changed = True
        if merged_urls:
            inp["urls"] = merged_urls

    # image：缺失才补
    if not existing.get("image"):
        images = performer_data.get("images") or []
        if images:
            inp["image"] = images[0]
            changed = True

    if not changed:
        return False

    inp = {k: v for k, v in inp.items() if v is not None and v != []}
    data = await client.post(Q.PERFORMER_UPDATE, {"input": inp})
    if data and data.get("performerUpdate"):
        logger.info("         - 👤 更新演员字段 %s (%d 项)", existing.get("name"), sum(1 for _ in inp) - 1)
        return True
    logger.warning("         - ⚠️ 演员更新失败: %s", existing.get("name"))
    return False


def compare_performers(current_performers, scraped_performers):
    """比较当前和刮削演员列表，返回需要添加的演员。"""
    current_names = {p.get("name", "").lower() for p in current_performers}
    to_add = []
    for sp in scraped_performers:
        sname = sp.get("name", "").lower()
        if sname and sname not in current_names:
            to_add.append(sp)
    return to_add