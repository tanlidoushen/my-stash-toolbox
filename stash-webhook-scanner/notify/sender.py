"""TG 统一发送层（2026-08-17 阶段一：统一 send_notification 与 soft_delete 确认消息）。

统一封装所有 TG 消息发送：
- bot 对象优先（python-telegram-bot），httpx 裸调兜底
- 支持 send_message / send_photo / 内联按钮 / 自动删除
- 各业务模块只调 send_html，不再各自拼发送逻辑

用法：
    from notify.sender import send_html
    ok = await send_html(chat_id, text, bot=bot, img_data=img_bytes,
                         reply_markup={"inline_keyboard": [...]},
                         auto_delete_delay=30)
"""
import io
import logging

import httpx

from config import Config

logger = logging.getLogger(__name__)


async def send_html(chat_id, text, bot=None, img_data=None, reply_markup=None,
                    auto_delete_delay=None, filename="photo.jpg"):
    """统一发送 HTML 消息（文本或图片）。

    Args:
        chat_id: TG chat id
        text: HTML 消息文本
        bot: python-telegram-bot Bot 实例（优先）；None 走 httpx 裸调
        img_data: bytes / BytesIO / None —— 有则 sendPhoto，无则 sendMessage
        reply_markup: 内联键盘 dict（如 {"inline_keyboard": [...]}）
        auto_delete_delay: 秒数，>0 时自动删除消息（用 bot 对象时生效）
        filename: 图片文件名（httpx 兜底用）

    Returns:
        True=成功 / False=失败
    """
    if not chat_id:
        logger.warning("TG 通知未配置 chat_id，跳过")
        return False

    if bot is not None:
        return await _send_via_bot(bot, chat_id, text, img_data, reply_markup,
                                   auto_delete_delay)
    return await _send_via_httpx(chat_id, text, img_data, reply_markup, filename)


# ---------- python-telegram-bot 方式 ----------

async def _send_via_bot(bot, chat_id, text, img_data, reply_markup, auto_delete_delay):
    try:
        if img_data is not None:
            sent = await bot.send_photo(
                chat_id=chat_id, photo=img_data, caption=text,
                parse_mode="HTML", reply_markup=reply_markup,
            )
        else:
            sent = await bot.send_message(
                chat_id=chat_id, text=text, parse_mode="HTML",
                reply_markup=reply_markup,
            )
        if auto_delete_delay and auto_delete_delay > 0:
            from bot.javdb_search_state import _schedule_auto_delete
            _schedule_auto_delete(bot, sent.chat_id, sent.message_id, auto_delete_delay)
        logger.info("TG 推送成功 (bot)")
        return True
    except Exception as e:
        logger.error("TG 推送异常 (bot): %s", e)
        return False


# ---------- httpx 裸调兜底 ----------

async def _send_via_httpx(chat_id, text, img_data, reply_markup, filename):
    bot_token = Config.TG_BOT_TOKEN
    if not bot_token:
        logger.warning("TG 通知未配置 BOT_TOKEN，跳过")
        return False

    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as c:
        try:
            if img_data is not None:
                if isinstance(img_data, bytes):
                    img_data = io.BytesIO(img_data)
                img_data.seek(0)
                data_payload = {
                    "chat_id": chat_id, "caption": text, "parse_mode": "HTML",
                }
                if reply_markup:
                    data_payload["reply_markup"] = _json(reply_markup)
                url = "https://api.telegram.org/bot%s/sendPhoto" % bot_token
                resp = await c.post(url, data=data_payload,
                                    files={"photo": (filename, img_data, "image/jpeg")})
            else:
                data_payload = {
                    "chat_id": chat_id, "text": text, "parse_mode": "HTML",
                }
                if reply_markup:
                    data_payload["reply_markup"] = reply_markup
                url = "https://api.telegram.org/bot%s/sendMessage" % bot_token
                resp = await c.post(url, json=data_payload)

            if resp.status_code == 200:
                logger.info("TG 推送成功 (httpx)")
                return True
            logger.error("TG 推送失败 (httpx, HTTP %d): %s", resp.status_code, resp.text)
            return False
        except Exception as e:
            logger.error("TG 推送异常 (httpx): %s", e)
            return False


def _json(obj):
    import json
    return json.dumps(obj)
