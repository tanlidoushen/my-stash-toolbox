"""JavDB Search —— Telegram 命令/回调处理器。
"""

import asyncio
import html
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from config import Config
from bot.magnet_sources import get_magnet_manager
from bot.magnet_sources.base import MagnetInfo, MovieInfo

from bot.javdb_search_state import (
    _cancel_auto_delete,
    _detail_cache,
    _magnet_cache,
    _monitor_tasks,
    _scene_link_cache,
    _schedule_auto_delete,
    MonitorState,
)
from bot.javdb_search_utils import (
    _download_cover,
)
from bot.javdb_search_format import (
    _build_search_buttons,
    _build_stash_link,
    _format_detail_with_buttons,
    _format_search_caption,
    _stash_lookup,
)
from bot.magnet_sources import get_magnet_manager
from bot.javdb_search_offline import _monitor_offline_task
from bot.utils import safe_edit_text

logger = logging.getLogger(__name__)


# ═══════════════════════════ /code 搜索命令 ═══════════════════════════

async def cmd_javdb_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /code <番号> 命令。"""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "请提供番号。\n"
            "用法：/code 番号\n"
            "例如：/code MIDA-708",
            parse_mode="HTML",
        )
        return

    query_code = " ".join(context.args)
    normalised = query_code.upper().replace("_", "-")

    status_msg = await update.message.reply_text(
        "正在搜索 <b>%s</b>…" % normalised, parse_mode="HTML"
    )

    loop = asyncio.get_running_loop()
    manager = get_magnet_manager()

    async def _do_search():
        movies = await manager.search_movies(normalised, limit=12)
        return movies

    movies = await _do_search()

    if not movies:
        await status_msg.edit_text(
            "搜索结果: %s\n\n未找到匹配结果。" % normalised,
            parse_mode="HTML",
        )
        return

    # ── 自动选定（可配置）：内部能判断则直接进详情，跳过候选列表 ──
    picked = None
    if getattr(Config, "MAGNET_AUTO_PICK_ENABLED", True):
        picked = manager.pick_movie_auto(movies, normalised)

    if picked is not None:
        _cancel_auto_delete(status_msg.message_id)
        movie, movie_dict, magnet_infos, stash_map, avdb_cover = await _fetch_detail_data(
            picked.id, source=picked.source_name
        )
        if movie_dict:
            logger.info("[JavDB Search] 自动选定影片: %s (%s) id=%s",
                        picked.number, picked.source_name, picked.id)
            await _render_detail(status_msg, movie, movie_dict, magnet_infos, stash_map, avdb_cover)
            _schedule_auto_delete(context.bot, status_msg.chat_id, status_msg.message_id,
                                  Config.SEARCH_AUTO_DELETE_DELAY)
            return
        logger.warning("[JavDB Search] 自动选定影片 %s 详情获取失败，回退候选列表", picked.id)

    caption = _format_search_caption(normalised, [m.to_dict() for m in movies[:5]], len(movies))
    reply_markup = _build_search_buttons([m.to_dict() for m in movies[:5]])

    # 尝试下载并发送封面图（MovieInfo.cover_url 已是完整可下载 URL 时直接用）
    first_cover_url = movies[0].cover_url or ""
    photo_sent = False
    if first_cover_url:
        try:
            cover_bytes = await loop.run_in_executor(None, _download_cover, first_cover_url)
            if cover_bytes:
                await status_msg.delete()
                sent_msg = await update.message.reply_photo(
                    photo=cover_bytes,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
                _schedule_auto_delete(context.bot, sent_msg.chat_id, sent_msg.message_id, Config.SEARCH_AUTO_DELETE_DELAY)
                photo_sent = True
        except Exception as e:
            logger.warning("[JavDB Search] 发送封面失败: %s", e)

    if not photo_sent:
        try:
            await status_msg.edit_text(caption, reply_markup=reply_markup, parse_mode="HTML")
            _schedule_auto_delete(context.bot, status_msg.chat_id, status_msg.message_id, Config.SEARCH_AUTO_DELETE_DELAY)
        except BadRequest:
            sent_msg = await update.message.reply_text(caption, reply_markup=reply_markup, parse_mode="HTML")
            _schedule_auto_delete(context.bot, sent_msg.chat_id, sent_msg.message_id, Config.SEARCH_AUTO_DELETE_DELAY)


# ═══════════════════════════ 详情展示 ═══════════════════════════

async def _edit_caption(editable, **kwargs):
    """编辑消息 caption：兼容 CallbackQuery(edit_message_caption) 与 Message(edit_caption)。"""
    if hasattr(editable, "edit_message_caption"):
        return await editable.edit_message_caption(**kwargs)
    return await editable.edit_caption(**kwargs)


async def _edit_media(editable, **kwargs):
    """编辑消息媒体：兼容 CallbackQuery(edit_message_media) 与 Message(edit_media)。"""
    if hasattr(editable, "edit_message_media"):
        return await editable.edit_message_media(**kwargs)
    return await editable.edit_media(**kwargs)


async def _edit_text(editable, **kwargs):
    """编辑消息文本：兼容 CallbackQuery(edit_message_text) 与 Message(edit_text)。"""
    if hasattr(editable, "edit_message_text"):
        return await editable.edit_message_text(**kwargs)
    return await editable.edit_text(**kwargs)


async def _fetch_detail_data(movie_id, source=None):
    """获取影片详情 + 磁力搜索（数据层，回调路径 / 自动选定路径共用）。

    Args:
        movie_id: 来源站影片 ID
        source: 指定来源插件名（自动选定路径传，避免 AVDB 把 JavDB id 当番号误搜）

    Returns:
        (movie, movie_dict, magnet_infos, stash_map, avdb_cover)
    """
    manager = get_magnet_manager()
    movie = await manager.get_movie_detail(movie_id, source=source)
    movie_dict = movie.to_dict() if movie else None

    # 磁力搜索：通过管理器并行搜索所有已启用的磁力源
    magnet_infos: list[MagnetInfo] = []
    avdb_cover = ""
    if movie_dict:
        number = (movie_dict.get("number") or "").strip()
        if number:
            magnet_infos = await manager.search_all(number)
            # 从结果中取第一条有预览图的作为兜底封面
            for m in magnet_infos:
                if m.preview_image:
                    avdb_cover = m.preview_image
                    break

    stash_map = await _stash_lookup(movie_dict) if movie_dict else {}
    return movie, movie_dict, magnet_infos, stash_map, avdb_cover


async def _render_detail(editable, movie, movie_dict, magnet_infos, stash_map, avdb_cover):
    """渲染详情到可编辑对象（CallbackQuery 或 Message，自动选定/回调共用）。

    封面：① 影片封面（MovieInfo.cover_url 完整 URL） ② AVDB 预览图兜底，
          都失败则回退纯文本。
    """
    detail_text, sorted_magnets, magnet_markup = _format_detail_with_buttons(
        movie_dict, magnet_infos, stash_map
    )
    _magnet_cache[movie_dict["id"]] = sorted_magnets
    # 本地 Stash 播放链接缓存（磁力分页切换时保留"查看原视频"行）
    _scene_link_cache[movie_dict["id"]] = _build_stash_link(stash_map)

    loop = asyncio.get_running_loop()

    async def _try_send_cover(candidates):
        """依次尝试候选封面 URL，成功发送图片则返回 True。"""
        for url in candidates:
            if not url:
                continue
            try:
                cover_bytes = await loop.run_in_executor(None, _download_cover, url)
                if cover_bytes:
                    await _edit_media(
                        editable,
                        media=InputMediaPhoto(media=cover_bytes, caption=detail_text, parse_mode="HTML"),
                        reply_markup=magnet_markup,
                    )
                    return True
            except Exception as e:
                logger.warning("[JavDB Detail] 发送封面失败 %s: %s", url[:80], e)
        return False

    javdb_cover = (movie.cover_url if movie else "") or ""
    if await _try_send_cover([javdb_cover, avdb_cover]):
        return

    # 回退到纯文本
    try:
        await _edit_text(editable, text=detail_text, reply_markup=magnet_markup, parse_mode="HTML")
    except BadRequest:
        pass


async def handle_javdb_detail(query, movie_id):
    """根据 movie_id 获取详情并替换当前消息（回调路径）。"""
    await query.answer()
    _cancel_auto_delete(query.message.message_id)

    movie, movie_dict, magnet_infos, stash_map, avdb_cover = await _fetch_detail_data(movie_id)

    if not movie_dict:
        try:
            await query.edit_message_caption(
                caption="获取详情失败，请稍后重试。", parse_mode="HTML"
            )
        except Exception:
            pass
        return

    await _render_detail(query, movie, movie_dict, magnet_infos, stash_map, avdb_cover)


# ═══════════════════════════ 磁力链接分页 ═══════════════════════════

async def handle_magnet_page(query, movie_id, page):
    """处理磁力链接分页切换。"""
    _cancel_auto_delete(query.message.message_id)

    magnets = _magnet_cache.get(movie_id)
    if not magnets:
        await safe_edit_text(query, "磁力链接缓存已过期，请重新搜索。", parse_mode="HTML")
        return

    from bot.javdb_search_format import _format_magnets
    magnet_text, sorted_magnets, magnet_markup = _format_magnets(
        magnets, movie_id=movie_id, page=page,
    )
    # 本地已有链接行在消息最顶部，分页重渲染时保留
    link = _scene_link_cache.get(movie_id, "")
    if link:
        magnet_text = link + "\n\n" + magnet_text

    try:
        await query.edit_message_caption(
            caption=magnet_text, parse_mode="HTML", reply_markup=magnet_markup,
        )
    except BadRequest:
        try:
            await query.edit_message_text(
                magnet_text, parse_mode="HTML", reply_markup=magnet_markup,
            )
        except BadRequest as e:
            if "not modified" not in str(e).lower():
                raise


# ═══════════════════════════ 添加离线下载 ═══════════════════════════

async def handle_magnet_add(query, movie_id, idx):
    """展示目录选择菜单，供用户选择离线下载目标目录。"""
    await query.answer()

    magnets = _magnet_cache.get(movie_id)
    if not magnets:
        await safe_edit_text(query, "磁力链接缓存已过期，请重新搜索。", parse_mode="HTML")
        return

    if idx < 0 or idx >= len(magnets):
        await safe_edit_text(query, "无效的磁力链接索引。", parse_mode="HTML")
        return

    magnet = magnets[idx]
    # title 可能来自第三方标题（含 <> 等字符），嵌入 HTML 消息前转义
    name = html.escape((magnet.title or "未命名").strip())

    folders = getattr(Config, "CD2_OFFLINE_FOLDERS", None)
    if not folders:
        folders = {"影片目录": Config.CD2_OFFLINE_FOLDER}

    dir_keys = list(folders.keys())
    if len(dir_keys) == 1:
        await handle_magnet_dir_pick(query, movie_id, idx, 0)
        return

    dir_buttons = []
    for di, dk in enumerate(dir_keys):
        dir_buttons.append([
            InlineKeyboardButton("📁 目录: %s" % dk, callback_data="mag_dir_%s_%d_%d" % (movie_id, idx, di))
        ])
    dir_buttons.append([
        InlineKeyboardButton("⬅️ 返回详情", callback_data="javdb_pick_%s" % movie_id)
    ])

    await safe_edit_text(
        query,
        "选择下载目录\n\n磁力: %s" % name,
        reply_markup=InlineKeyboardMarkup(dir_buttons),
        parse_mode="HTML",
    )


async def handle_magnet_dir_pick(query, movie_id, idx, dir_idx, bot=None, mover_handler=None):
    """选择目录后：添加到 CD2，然后在新消息中监控进度。"""
    await query.answer("正在添加离线下载…")

    magnets = _magnet_cache.get(movie_id)
    if not magnets:
        await safe_edit_text(query, "磁力链接缓存已过期，请重新搜索。", parse_mode="HTML")
        return

    if idx < 0 or idx >= len(magnets):
        await safe_edit_text(query, "无效的磁力链接索引。", parse_mode="HTML")
        return

    folders = getattr(Config, "CD2_OFFLINE_FOLDERS", None)
    if not folders:
        folders = {"影片目录": Config.CD2_OFFLINE_FOLDER}
    dir_keys = list(folders.keys())

    if dir_idx < 0 or dir_idx >= len(dir_keys):
        await safe_edit_text(query, "无效的目录选择。", parse_mode="HTML")
        return

    dir_key = dir_keys[dir_idx]
    target_folder = folders[dir_key]

    magnet = magnets[idx]
    magnet_hash = magnet.hash or ""
    # AVDB 磁力带完整 url（含 &dn= 等参数）时优先使用；JavDB 磁力无 url，走 hash 拼接
    magnet_url = magnet.url or (
        "magnet:?xt=urn:btih:%s" % magnet_hash if magnet_hash else ""
    )
    # title 可能来自第三方标题（含 <> 等字符），嵌入 HTML 消息前转义
    name = html.escape((magnet.title or "未命名").strip())
    size_mb = magnet.size_mb or 0
    size_str = "%.1f GB" % (size_mb / 1024) if size_mb >= 1024 else "%d MB" % size_mb

    if not magnet_url or not magnet_url.startswith("magnet:"):
        await safe_edit_text(
            query, "无效的磁力链接:\n<code>%s</code>" % name, parse_mode="HTML"
        )
        return

    from stash.cd2_offline import add_offline_download

    ok, err = await add_offline_download(magnet_url, target_folder)

    badges = []
    if "中字" in (magnet.tags or []):
        badges.append("中字")
    if "高清" in (magnet.tags or []):
        badges.append("高清")
    badge_str = " (%s)" % " · ".join(badges) if badges else ""

    is_dup = err and ("已存在" in err or "exist" in err.lower() or "duplicate" in err.lower() or "重复" in err)

    if not ok and not is_dup:
        text = (
            "添加失败\n\n"
            "磁力: %s%s\n"
            "大小: %s\n"
            "目录: %s\n"
            "错误: %s"
        ) % (name, badge_str, size_str, target_folder, html.escape(err))
        back_btn = InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ 返回详情", callback_data="javdb_pick_%s" % movie_id)
        ]])
        await safe_edit_text(query, text, parse_mode="HTML", reply_markup=back_btn)
        return

    interval = Config.CD2_OFFLINE_CHECK_INTERVAL
    initial_wait = Config.CD2_OFFLINE_INITIAL_WAIT

    if is_dup:
        logger.info("[offline] duplicate task, monitor anyway: %s", magnet_hash)
        restore_text = (
            "任务已存在，开始监控\n\n"
            "磁力: %s%s\n"
            "大小: %s\n"
            "目录: %s"
        ) % (name, badge_str, size_str, target_folder)
    else:
        restore_text = (
            "已添加离线下载\n\n"
            "磁力: %s%s\n"
            "大小: %s\n"
            "目录: %s"
        ) % (name, badge_str, size_str, target_folder)

    back_btn = InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ 返回详情", callback_data="javdb_pick_%s" % movie_id)
    ]])
    if bot is None:
        bot = query.bot

    chat_id = query.message.chat_id

    await safe_edit_text(query, restore_text, parse_mode="HTML", reply_markup=back_btn)
    _schedule_auto_delete(bot, chat_id, query.message.message_id, Config.SEARCH_AUTO_DELETE_DELAY)

    # 发送新的监控消息
    if is_dup:
        initial_text = "任务已存在，开始监控。将在 %d 秒后检查任务状态。" % initial_wait
    else:
        initial_text = "添加离线任务成功。将在 %d 秒后检查任务状态。" % initial_wait
    monitor_msg = await bot.send_message(chat_id=chat_id, text=initial_text, parse_mode="HTML")
    monitor_btns = InlineKeyboardMarkup([[
        InlineKeyboardButton("⚡ 立即检查", callback_data="mon_check_%d" % monitor_msg.message_id),
        InlineKeyboardButton("❌ 关闭提示", callback_data="mon_close_%d" % monitor_msg.message_id),
    ]])
    await bot.edit_message_reply_markup(
        chat_id=chat_id, message_id=monitor_msg.message_id,
        reply_markup=monitor_btns,
    )

    state = MonitorState()
    _monitor_tasks[monitor_msg.message_id] = state
    state.task = asyncio.create_task(
        _monitor_offline_task(
            bot=bot,
            chat_id=chat_id,
            message_id=monitor_msg.message_id,
            magnet_hash=magnet_hash,
            name=name,
            badge_str=badge_str,
            size_str=size_str,
            target_folder=target_folder,
            movie_id=movie_id,
            interval=interval,
            initial_wait=initial_wait,
            state=state,
            mover_handler=mover_handler,
        )
    )
