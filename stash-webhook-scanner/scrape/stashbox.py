"""stash-box 刮削：javstash 按番号刮削 + 通用 stash-box 刮削。"""

import logging

from stash import query as Q
import asyncio
from config import Config

logger = logging.getLogger(__name__)


async def scrape_japanese_scene(client, japanese_code, stash_box_index=0):
    """通过 stash-box endpoint 按番号刮削 JAV 场景元数据。
    返回刮削结果 dict，失败返回 None。
    """
    endpoint = await client.get_endpoint(stash_box_index)
    variables = {
        "source": {"stash_box_endpoint": endpoint},
        "input": {"query": japanese_code},
    }
    logger.info(
        "         - javstash 刮削 | 番号=%s | index=%d | %s",
        japanese_code, stash_box_index, endpoint,
    )

    for attempt in range(1, Config.JAV_SCRAPE_RETRY_COUNT + 1):
        try:
            data = await client.post(Q.SCRAPE_SINGLE_SCENE, variables)
            if data is None:
                if attempt < Config.JAV_SCRAPE_RETRY_COUNT:
                    logger.info(
                        "         - 重试 %d/%d，等待 %ds...",
                        attempt, Config.JAV_SCRAPE_RETRY_COUNT, Config.JAV_SCRAPE_RETRY_DELAY,
                    )
                    await asyncio.sleep(Config.JAV_SCRAPE_RETRY_DELAY)
                    continue
                return None
        except Exception as e:
            logger.error("         - ERROR 请求异常: %s", e)
            if attempt < Config.JAV_SCRAPE_RETRY_COUNT:
                logger.info(
                    "         - 重试 %d/%d，等待 %ds...",
                    attempt, Config.JAV_SCRAPE_RETRY_COUNT, Config.JAV_SCRAPE_RETRY_DELAY,
                )
                await asyncio.sleep(Config.JAV_SCRAPE_RETRY_DELAY)
                continue
            return None

        scraped = data.get("scrapeSingleScene")
        if isinstance(scraped, list):
            if len(scraped) == 0:
                logger.warning("         - ⚠️ 刮削返回空列表")
                if attempt < Config.JAV_SCRAPE_RETRY_COUNT:
                    await asyncio.sleep(Config.JAV_SCRAPE_RETRY_DELAY)
                    continue
                return None
            scraped = scraped[0]
        if not scraped:
            logger.warning("         - ⚠️ 刮削无结果")
            if attempt < Config.JAV_SCRAPE_RETRY_COUNT:
                await asyncio.sleep(Config.JAV_SCRAPE_RETRY_DELAY)
                continue
            return None

        logger.info(
            "         - ✅ 刮削成功 | %s | stash_id=%s",
            scraped.get("title"), scraped.get("remote_site_id"),
        )
        return scraped

    return None


async def scrape_scene(client, scene_id, stash_box_index=0):
    """使用 Stash-box metadataIdentify 进行刮削。返回 job_id 或 None。"""
    query_str = Q.METADATA_IDENTIFY.replace("IDX", str(stash_box_index)).replace(
        "SID", str(scene_id)
    )
    data = await client.post(query_str, {})
    if data is None:
        return None
    job_id = data.get("metadataIdentify")
    logger.info("         - 🚀 刮削任务已提交 | 场景 %s | 任务ID=%s", scene_id, job_id)
    return job_id


async def scrape_scene_by_remote_id(client, scene_id, stash_id, stash_box_index=0):
    """使用 stash-box scrapeSingleScene 根据远程 stash_id 重新刮削场景完整元数据。"""
    endpoint = await client.get_endpoint(stash_box_index)
    variables = {
        "source": {"stash_box_endpoint": endpoint},
        "input": {
            "scene_id": str(scene_id),
            "scene_input": {"remote_site_id": stash_id},
        },
    }
    data = await client.post(Q.SCRAPE_SINGLE_SCENE, variables)
    if data is None:
        return None
    scraped = data.get("scrapeSingleScene")
    if not scraped:
        return None
    if isinstance(scraped, list):
        if not scraped:
            logger.warning(
                "         - ⚠️ 场景 %s 通过 stash_id=%s 刮削无结果",
                scene_id, stash_id,
            )
            return None
        for item in scraped:
            if item.get("remote_site_id") == stash_id:
                return item
        logger.warning("         - ⚠️ 场景 %s 未找到完全匹配，使用第一个结果", scene_id)
        return scraped[0]
    return scraped
