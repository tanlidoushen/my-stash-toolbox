"""标签操作：查找、创建、比较、规范化。"""

import logging

from stash import query as Q

logger = logging.getLogger(__name__)
_tag_cache = None


async def _get_all_tags_cached(client):
    """惰性加载全部标签缓存。"""
    global _tag_cache
    if _tag_cache is not None:
        return _tag_cache
    data = await client.post(Q.FIND_TAGS, {"filter": {"per_page": -1}})
    if data:
        _tag_cache = data.get("findTags", {}).get("tags", [])
    else:
        _tag_cache = []
    return _tag_cache


async def get_tag_with_aliases(client, tag_name):
    """查找标签（含别名匹配）。返回 tag dict 或 None。"""
    tags = await _get_all_tags_cached(client)
    for t in tags:
        if t.get("name", "").lower() == tag_name.lower():
            return t
    for t in tags:
        aliases = t.get("aliases", [])
        while aliases:
            if tag_name.lower() in [a.lower() for a in aliases]:
                return t
            break
    return None


async def create_or_find_tag(client, tag_name, verbose=True):
    """创建或查找标签，返回 tag_id 或 None。"""
    tag = await get_tag_with_aliases(client, tag_name)
    if tag:
        return tag["id"]
    data = await client.post(Q.TAG_CREATE, {"input": {"name": tag_name}})
    if data and data.get("tagCreate"):
        tid = data["tagCreate"]["id"]
        if verbose:
            logger.info("         - 🏷️ 创建新标签: %s", tag_name)
        _tag_cache = None  # 失效缓存
        return tid
    logger.warning("         - ⚠️ 标签创建失败: %s", tag_name)
    return None


async def get_all_tags_with_aliases(client):
    """获取所有标签（含别名）。返回 dict {canonical_name: [aliases]}。"""
    tags = await _get_all_tags_cached(client)
    return {t["name"]: t.get("aliases", []) for t in tags}


def normalize_tag_name(tag_name, all_tags):
    """规范化标签名：优先匹配规范名，然后别名。"""
    for canonical, aliases in all_tags.items():
        if tag_name.lower() == canonical.lower():
            return canonical
        for alias in aliases:
            if tag_name.lower() == alias.lower():
                return canonical
    return tag_name


async def compare_tags(client, current_tags, scraped_tags):
    """比较当前标签和刮削标签。返回 (need_update, reason, merged_tag_names)。"""
    current_tags = current_tags or []
    scraped_tags = scraped_tags or []
    all_tags = await get_all_tags_with_aliases(client)

    current_norm = {normalize_tag_name(t["name"], all_tags) for t in current_tags}
    scraped_norm = {normalize_tag_name(t["name"], all_tags) for t in scraped_tags}

    if not current_norm and not scraped_norm:
        return False, "双方无标签", []
    if scraped_norm.issubset(current_norm):
        return False, "刮削标签是当前标签的子集", []

    new_tags = scraped_norm - current_norm
    if new_tags:
        merged = current_norm | scraped_norm
        return True, "发现 %d 个新标签" % len(new_tags), list(merged)
    return False, "无变化", []
