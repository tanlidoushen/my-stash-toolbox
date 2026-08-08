import asyncio
"""元数据补充：对 stash-box 刮削完成的 Non-JAV 场景进行元数据补充。"""

import logging

from stash import scene as scene_mod
from stash import tag as tag_mod
from stash import performer as performer_mod
from stash import studio as studio_mod
from config import Config

logger = logging.getLogger(__name__)


async def update_scene_metadata(client, scene_id, scraped_data, current_scene_info, stash_box_index=0):
    """比对刮削元数据与当前场景数据，差异化更新 Non-JAV 场景。"""
    inp = {"id": str(scene_id)}

    # ---- 基础字段 ----
    for field in ("title", "code", "date", "director", "details"):
        val = scraped_data.get(field)
        if val:
            inp[field] = val

    # ---- 封面 ----
    cover_image = scraped_data.get("image")
    if cover_image:
        inp["cover_image"] = cover_image

    # ---- 工作室 ----
    scraped_studio = scraped_data.get("studio")
    if scraped_studio:
        if scraped_studio.get("stored_id"):
            inp["studio_id"] = scraped_studio["stored_id"]
        elif scraped_studio.get("name"):
            studio_id = await studio_mod.create_or_find_studio(
                client, scraped_studio, stash_box_index
            )
            if studio_id:
                inp["studio_id"] = studio_id

    # ---- 演员 ----
    scraped_performers = scraped_data.get("performers", [])
    current_performers = (current_scene_info or {}).get("performers", [])
    performer_ids = [p["id"] for p in current_performers if p.get("id")]
    for p in scraped_performers:
        if not p.get("name"):
            continue
        if p.get("stored_id"):
            if p["stored_id"] not in performer_ids:
                performer_ids.append(p["stored_id"])
        else:
            pid = await performer_mod.create_or_find_performer(client, p, stash_box_index)
            if pid and pid not in performer_ids:
                performer_ids.append(pid)
    if performer_ids:
        inp["performer_ids"] = performer_ids

    # ---- 标签 ----
    scraped_tags = scraped_data.get("tags", [])
    current_tags = (current_scene_info or {}).get("tags", [])
    need_update_tags, reason, merged_names = await tag_mod.compare_tags(
        client, current_tags, scraped_tags
    )
    if need_update_tags:
        tag_ids = [t["id"] for t in current_tags]
        for tag_name in merged_names:
            all_tags = await tag_mod.get_all_tags_with_aliases(client)
            norm_current = {
                tag_mod.normalize_tag_name(t["name"], all_tags) for t in current_tags
            }
            if tag_mod.normalize_tag_name(tag_name, all_tags) not in norm_current:
                tid = await tag_mod.create_or_find_tag(client, tag_name)
                if tid:
                    tag_ids.append(tid)
    else:
        tag_ids = [t["id"] for t in current_tags]

    # Non-JAV 标签
    non_jav_tag_id = await tag_mod.create_or_find_tag(client, "Non-JAV", verbose=False)
    if non_jav_tag_id and non_jav_tag_id not in tag_ids:
        tag_ids.append(non_jav_tag_id)
    if tag_ids:
        inp["tag_ids"] = tag_ids

    # ---- 提交更新 ----
    inp = {k: v for k, v in inp.items() if v is not None and v != [] and v != {} and v != ""}
    if len(inp) == 1:
        logger.info("         - ⏭️ 无任何变更，跳过更新")
        return True

    return await scene_mod.update_scene(client, inp)


async def enrich_scene_metadata(client, scene_id, stash_id, stash_box_index=0):
    """对 stash-box 刮削完成的 Non-JAV 场景进行元数据补充。"""
    from scrape.stashbox import scrape_scene_by_remote_id

    scraped = await scrape_scene_by_remote_id(client, scene_id, stash_id, stash_box_index)
    if not scraped:
        logger.warning("      - ⚠️ 场景 %s 刮削无结果", scene_id)
        return False

    current_info = await scene_mod.get_scene_info(client, scene_id)
    return await update_scene_metadata(client, scene_id, scraped, current_info, stash_box_index)

