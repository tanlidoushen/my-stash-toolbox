"""演员操作：查找、创建。"""

import logging

from stash import query as Q

logger = logging.getLogger(__name__)


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


async def create_or_find_performer(client, performer_data, stash_box_index=0):
    """创建或查找演员，返回 performer_id 或 None。"""
    name = performer_data.get("name", "")
    if not name:
        return None
    existing = await find_performer_by_name(client, name)
    if existing:
        return existing["id"]

    # ---- 构建创建输入 ----
    input_data = {"name": name}
    for field in ("gender", "birthdate", "country", "measurements"):
        val = performer_data.get(field)
        if val:
            input_data[field] = val

    # 新增详细字段（stash-box 返回的可选字段）
    for field in ("disambiguation", "ethnicity", "eye_color", "hair_color",
                   "fake_tits", "career_start", "career_end", "tattoos"):
        val = performer_data.get(field)
        if val:
            input_data[field] = val

    # height -> height_cm (PerformerCreateInput 只支持 height_cm: Int)
    height_val = performer_data.get("height")
    if height_val:
        try:
            input_data["height_cm"] = int(height_val)
        except (ValueError, TypeError):
            pass

    # alias_list: 处理字符串和列表
    raw_aliases = performer_data.get("aliases")
    if isinstance(raw_aliases, str):
        aliases = [a.strip() for a in raw_aliases.split(",") if a.strip()]
    elif isinstance(raw_aliases, list):
        aliases = raw_aliases
    else:
        aliases = []
    if aliases:
        input_data["alias_list"] = aliases

    # urls
    urls = performer_data.get("urls")
    if urls:
        input_data["urls"] = urls

    # image: 取 images 列表的第一张
    images = performer_data.get("images") or []
    if images:
        input_data["image"] = images[0]

    # stash_ids: 关联 stash-box 远程 ID
    remote_site_id = performer_data.get("remote_site_id")
    if remote_site_id:
        endpoint_url = await client.get_endpoint(stash_box_index)
        input_data["stash_ids"] = [
            {"endpoint": endpoint_url, "stash_id": remote_site_id}
        ]

    # 移除空值
    input_data = {k: v for k, v in input_data.items() if v is not None and v != []}

    data = await client.post(Q.PERFORMER_CREATE, {"input": input_data})
    if data and data.get("performerCreate"):
        pid = data["performerCreate"]["id"]
        logger.info("         - 👤 创建新演员: %s", name)
        return pid
    logger.warning("         - ⚠️ 演员创建失败: %s", name)
    return None


def compare_performers(current_performers, scraped_performers):
    """比较当前和刮削演员列表，返回需要添加的演员。"""
    current_names = {p.get("name", "").lower() for p in current_performers}
    to_add = []
    for sp in scraped_performers:
        sname = sp.get("name", "").lower()
        if sname and sname not in current_names:
            to_add.append(sp)
    return to_add
