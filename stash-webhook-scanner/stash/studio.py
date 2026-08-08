"""片商操作：查找、创建。"""

import logging

from stash import query as Q

logger = logging.getLogger(__name__)


async def find_studio_by_name(client, studio_name):
    """根据名称查找工作室。"""
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


async def create_or_find_studio(client, studio_data, stash_box_index=0):
    """查找或创建工作室（含父工作室递归创建）。"""
    name = studio_data.get("name")
    if not name:
        return None

    existing_id = await find_studio_by_name(client, name)
    if existing_id:
        return existing_id

    endpoint = await client.get_endpoint(stash_box_index)
    inp = {"name": name}
    if studio_data.get("url"):
        inp["url"] = studio_data["url"]
    if studio_data.get("details"):
        inp["details"] = studio_data["details"]
    if studio_data.get("image"):
        inp["image"] = studio_data["image"]
    if studio_data.get("aliases"):
        inp["aliases"] = studio_data["aliases"]
    if studio_data.get("remote_site_id"):
        inp["stash_ids"] = [{"endpoint": endpoint, "stash_id": studio_data["remote_site_id"]}]

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
