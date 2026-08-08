"""Bot 模块通用工具函数。"""

import asyncio
import logging

from telegram.error import BadRequest

logger = logging.getLogger(__name__)

# 自删除定时器：message_id -> asyncio.Task
_pending_deletion: dict[int, asyncio.Task] = {}


def _cancel_auto_delete(message_id: int):
    """取消指定消息的自动删除定时器。"""
    task = _pending_deletion.pop(message_id, None)
    if task and not task.done():
        task.cancel()


def _schedule_auto_delete(bot, chat_id: int, message_id: int, delay: int = 300):
    """在 delay 秒后自动删除指定消息。"""
    _cancel_auto_delete(message_id)

    async def _delete():
        try:
            await asyncio.sleep(delay)
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass
        finally:
            _pending_deletion.pop(message_id, None)

    task = asyncio.create_task(_delete())
    _pending_deletion[message_id] = task


async def safe_edit_text(query, text, **kwargs):
    """安全编辑消息文本，兼容 text 和 photo 消息。

    - 连续点击相同按钮时静默忽略 "not modified"
    - Photo 消息自动回退到 edit_message_caption
    """
    try:
        await query.edit_message_text(text, **kwargs)
    except BadRequest as e:
        msg = str(e).lower()
        if "not modified" in msg:
            return
        if "there is no text" in msg:
            try:
                await query.edit_message_caption(
                    caption=text,
                    parse_mode=kwargs.get("parse_mode"),
                    reply_markup=kwargs.get("reply_markup"),
                )
            except BadRequest as e2:
                if "not modified" not in str(e2).lower():
                    raise
            return
        raise


async def safe_delete_message(query):
    """安全删除消息，消息已不存在时静默忽略。"""
    try:
        await query.delete_message()
    except BadRequest:
        pass


def fmt_file_size(f):
    """格式化文件路径和大小，返回 HTML 片段。"""
    path = f.get("path", "?")
    size_bytes = f.get("size", 0) or 0
    if size_bytes:
        size_gb = round(size_bytes / (1024 ** 3), 2)
        return f"  • <code>{path}</code> — {size_gb} GB"
    return f"  • <code>{path}</code>"
