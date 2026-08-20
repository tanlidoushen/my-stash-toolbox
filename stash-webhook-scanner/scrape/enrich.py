"""元数据补充：对 stash-box 刮削完成的 Non-JAV 场景进行元数据补充。

2026-08-17 重构：写库核心逻辑统一到 scrape/update.update_scene_metadata，
本模块的 update_scene_metadata 保留为兼容入口（转发到公共模块）。
"""
import asyncio

import logging

from stash import scene as scene_mod
from scrape.update import update_scene_metadata  # noqa: F401  # 兼容转发

logger = logging.getLogger(__name__)


async def enrich_scene_metadata(client, scene_id, stash_id, stash_box_index=0):
    """对 stash-box 刮削完成的 Non-JAV 场景进行元数据补充。"""
    from scrape.stashbox import scrape_scene_by_remote_id

    scraped = await scrape_scene_by_remote_id(client, scene_id, stash_id, stash_box_index)
    if not scraped:
        logger.warning("      - ⚠️ 场景 %s 刮削无结果", scene_id)
        return False

    current_info = await scene_mod.get_scene_info(client, scene_id)
    return await update_scene_metadata(
        client, scene_id, scraped, stash_box_index,
        current_scene_info=current_info, add_tag="Non-JAV",
    )
