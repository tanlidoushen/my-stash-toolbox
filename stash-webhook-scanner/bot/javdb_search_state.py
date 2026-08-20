"""JavDB Search —— 全局状态 / 缓存 / 自动删除定时器。
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

# 进程级缓存 web_image_prefix（startup 接口结果不会频繁变化）
_image_prefix_cache = None

# 进程级缓存磁力链接（movie_id -> sorted_magnets_list）
_magnet_cache = {}
_detail_cache = {}

# 进程级缓存本地 Stash 播放链接（movie_id -> HTML 链接行，分页切换时保留）
_scene_link_cache = {}

# 自删除定时器：message_id -> asyncio.Task，5分钟无交互自动删除 /code 的回复
_pending_deletion: dict[int, asyncio.Task] = {}


class MonitorState:
    __slots__ = ("check_now", "cancelled", "task")

    def __init__(self):
        self.check_now = asyncio.Event()
        self.cancelled = False
        self.task: asyncio.Task | None = None


_monitor_tasks: dict[int, MonitorState] = {}


def _cancel_auto_delete(message_id: int):
    """取消指定消息的自动删除定时器。"""
    task = _pending_deletion.pop(message_id, None)
    if task and not task.done():
        task.cancel()


def _schedule_auto_delete(bot, chat_id: int, message_id: int, delay: int = 300):
    """在 delay 秒后自动删除指定消息。"""
    # 取消已有的定时器（如果有）
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