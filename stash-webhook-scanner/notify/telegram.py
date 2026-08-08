"""Telegram 通知：截图下载 + 消息发送。

优先通过 python-telegram-bot 的 bot 对象发送，
bot 不可用时回退到 httpx 裸调 REST API。
"""

import io
import logging

import httpx

from config import Config
from notify.builder import get_scene_data, build_caption

logger = logging.getLogger(__name__)


async def send_notification(client, scene_id, is_japanese, target_chat_id=None, bot=None):
    """完整流程：查询场景 -> 构建消息 -> 下载截图 -> 推送 TG。

    Parameters
    ----------
    bot : telegram.Bot | None
        python-telegram-bot 的 Bot 实例。传入时优先使用 bot 对象发消息
        （TranscriberBot 风格）；不传则走 httpx 裸调 REST API 兜底。
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

    # 2. 构建消息文本
    caption = await build_caption(scene, is_japanese, client, stash_base_url)

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

    # 4. 推送至 TG
    if bot is not None:
        return await _send_via_bot(bot, chat_id, caption, img_data, scene_id)
    else:
        return await _send_via_httpx(caption, chat_id, img_data, scene_id)


# ---------- python-telegram-bot 方式（TranscriberBot 风格） ----------

async def _send_via_bot(bot, chat_id, caption, img_data, scene_id):
    """通过 bot 对象发送消息，与 TranscriberBot 保持一致。"""
    try:
        if img_data is not None:
            await bot.send_photo(
                chat_id=chat_id,
                photo=img_data,
                caption=caption,
                parse_mode="HTML",
            )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=caption,
                parse_mode="HTML",
            )
        logger.info("场景 %s TG 推送成功 (bot)", scene_id)
        return True
    except Exception as e:
        logger.error("场景 %s TG 推送异常 (bot): %s", scene_id, e)
        return False


# ---------- httpx 裸调兜底（scrape/pipeline 等无 bot 上下文时使用） ----------

async def _send_via_httpx(caption, chat_id, img_data, scene_id):
    """通过 httpx 裸调 Telegram REST API 发送消息。"""
    bot_token = Config.TG_BOT_TOKEN
    if not bot_token:
        logger.warning("TG 通知未配置 BOT_TOKEN，跳过场景 %s", scene_id)
        return False

    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as tg_client:
        try:
            if img_data is not None:
                img_data.seek(0)
                files_payload = {"photo": ("screenshot.jpg", img_data, "image/jpeg")}
                data_payload = {
                    "chat_id": chat_id,
                    "caption": caption,
                    "parse_mode": "HTML",
                }
                tg_url = "https://api.telegram.org/bot%s/sendPhoto" % bot_token
                resp = await tg_client.post(tg_url, data=data_payload, files=files_payload)
            else:
                data_payload = {
                    "chat_id": chat_id,
                    "text": caption,
                    "parse_mode": "HTML",
                }
                tg_url = "https://api.telegram.org/bot%s/sendMessage" % bot_token
                resp = await tg_client.post(tg_url, json=data_payload)

            if resp.status_code == 200:
                logger.info("场景 %s TG 推送成功 (httpx)", scene_id)
                return True
            else:
                logger.error("场景 %s TG 推送失败 (httpx, HTTP %d): %s",
                             scene_id, resp.status_code, resp.text)
                return False
        except Exception as e:
            logger.error("场景 %s TG 推送异常 (httpx): %s", scene_id, e)
            return False
