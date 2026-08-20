"""Telegram 通知：截图下载 + 消息发送。

2026-08-17 重构：发送层统一到 notify/sender.send_html，模板统一到
notify.builder.build_scene_card。本模块只负责「查询场景 → 下载截图 → 组装 → 发送」。
"""

import io
import logging

import httpx

from config import Config
from notify.sender import send_html
from notify.builder import get_scene_data, build_scene_card

logger = logging.getLogger(__name__)


async def send_notification(client, scene_id, is_japanese, target_chat_id=None, bot=None):
    """刮削完成通知：查询场景 -> 构建卡片 -> 下载截图 -> 统一发送。

    Parameters
    ----------
    bot : telegram.Bot | None
        python-telegram-bot 的 Bot 实例。传入时优先使用 bot 对象发消息
        ；不传则走 httpx 裸调 REST API 兜底。
    """
    chat_id = target_chat_id or Config.TG_CHAT_ID
    stash_base_url = Config.STASH_BASE_URL

    if not chat_id:
        logger.warning("TG 通知未配置 chat_id，跳过场景 %s", scene_id)
        return False

    logger.info(
        "准备推送 TG 通知 | 场景 %s | 区域=%s",
        scene_id, "JAV" if is_japanese else "Non-JAV",
    )

    # 1. 查询场景数据
    scene = await get_scene_data(client, scene_id)
    if not scene:
        logger.warning("场景 %s 数据查询失败，跳过 TG 通知", scene_id)
        return False

    # 2. 构建统一场景卡片
    caption = await build_scene_card(scene, is_japanese, client, stash_base_url)

    # 3. 下载截图
    screenshot_url = scene.get("paths", {}).get("screenshot")
    img_data = None
    if screenshot_url:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as img_client:
                img_resp = await img_client.get(screenshot_url)
                img_resp.raise_for_status()
                img_data = io.BytesIO(img_resp.content)
                img_data.name = "screenshot.jpg"
        except Exception as e:
            logger.warning("场景 %s 截图下载失败: %s，发送纯文本", scene_id, e)

    # 4. 统一发送
    return await send_html(chat_id, caption, bot=bot, img_data=img_data,
                           filename="screenshot.jpg")
