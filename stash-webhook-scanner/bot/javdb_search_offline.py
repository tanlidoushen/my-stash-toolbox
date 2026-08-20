"""JavDB Search —— 离线任务监控（提交离线下载后轮询 CD2 状态）。
"""

import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

from bot.javdb_search_state import MonitorState, _monitor_tasks

logger = logging.getLogger(__name__)


async def _monitor_offline_task(bot, chat_id, message_id, magnet_hash, name, badge_str,
                                size_str, target_folder, movie_id, interval, initial_wait, state=None, mover_handler=None):
    from stash.cd2_offline_check import query_offline_task_by_hash
    if state is None:
        state = MonitorState()
    logger.info("[offline] start monitor hash=%s target=%s wait=%ds interval=%ds",
                magnet_hash, target_folder, initial_wait, interval)
    try:
        await asyncio.wait_for(state.check_now.wait(), timeout=initial_wait)
    except asyncio.TimeoutError:
        pass
    if state.cancelled:
        return

    async def _edit(text, reply_markup=None):
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=reply_markup)
        except BadRequest as e:
            if "not modified" not in str(e).lower():
                logger.error("[offline] edit error: %s", e)

    def _btns(recheck=False):
        check_text = "🔄 重新检查" if recheck else "⚡ 立即检查"
        return InlineKeyboardMarkup([[InlineKeyboardButton(check_text, callback_data="mon_check_%d" % message_id), InlineKeyboardButton("❌ 关闭提示", callback_data="mon_close_%d" % message_id)]])

    close_only = InlineKeyboardMarkup([[InlineKeyboardButton("❌ 关闭提示", callback_data="mon_close_%d" % message_id)]])

    while not state.cancelled:
        state.check_now.clear()
        task = await query_offline_task_by_hash(magnet_hash, path=target_folder)

        if task is None:
            text = ("⌛ <b>当前离线任务监控</b>\n\n"
                    "🧲 <code>%s</code>%s\n"
                    "📦 大小: %s\n"
                    "📁 目录: <code>%s</code>\n\n"
                    "⏳ 等待任务出现…") % (name, badge_str, size_str, target_folder)
            await _edit(text, reply_markup=_btns(recheck=True))

        elif task["is_finished"]:
            task_name = task["name"] or name
            task_size = task["size"] or size_str
            text = ("✅ <b>离线任务已完成</b>\n\n"
                    "🧲 <code>%s</code>%s\n"
                    "名称: %s\n"
                    "大小: %s\n"
                    "目录: <code>%s</code>") % (task_name, badge_str, task_name, task_size, target_folder)
            await _edit(text, reply_markup=close_only)
            _monitor_tasks.pop(message_id, None)

            # ── 自动触发归类 ──
            trigger_name = None
            if mover_handler is not None and mover_handler.enabled:
                from config import Config
                rules = Config.get_mover_rules()
                for i, rule in enumerate(rules):
                    mp = rule.get("monitor_path", "")
                    if mp and mp == target_folder:
                        trigger_name = rule.get("name", "未命名")
                        logger.info("[offline] 离线完成，自动触发归类: [%s] %s", trigger_name, mp)
                        import threading
                        threading.Thread(
                            target=mover_handler._do_traverse_and_move,
                            kwargs={"rule_indices": [i]},
                            daemon=True,
                        ).start()
                        break

            # 消息末尾追加触发提示
            if trigger_name:
                text = text + "\n\n📦 已自动触发归类：[%s]" % trigger_name
                await _edit(text, reply_markup=close_only)

            return

        elif task["is_error"]:
            task_name = task["name"] or name
            task_size = task["size"] or size_str
            text = ("❌ <b>离线任务失败</b>\n\n"
                    "🧲 <code>%s</code>%s\n"
                    "名称: %s\n"
                    "大小: %s\n"
                    "目录: <code>%s</code>\n"
                    "状态: %s") % (task_name, badge_str, task_name, task_size, target_folder, task["status_text"])
            await _edit(text, reply_markup=close_only)
            _monitor_tasks.pop(message_id, None)
            return

        else:
            task_name = task["name"] or name
            task_size = task["size"] or size_str
            task_progress = task["progress"]
            progress_line = "进度: %.1f%%" % task_progress if task_progress > 0 else ""
            parts = ["📥 <b>当前离线任务</b>", "", "🧲 <code>%s</code>%s" % (task_name, badge_str), "状态: %s" % task["status_text"]]
            if progress_line:
                parts.append(progress_line)
            parts += ["名称: %s" % task_name, "大小: %s" % task_size, "目录: <code>%s</code>" % target_folder]
            text = "\n".join(parts)
            await _edit(text, reply_markup=_btns(recheck=True))

        try:
            await asyncio.wait_for(state.check_now.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass

    _monitor_tasks.pop(message_id, None)


async def handle_monitor_check(query, message_id):
    state = _monitor_tasks.get(message_id)
    if state and not state.cancelled:
        state.check_now.set()
    await query.answer("⚡ 正在检查…")


async def handle_monitor_close(query, message_id):
    state = _monitor_tasks.pop(message_id, None)
    if state:
        state.cancelled = True
        if state.task and not state.task.done():
            state.task.cancel()
    try:
        await query.message.delete()
    except Exception:
        pass
    await query.answer("✅ 已关闭")
