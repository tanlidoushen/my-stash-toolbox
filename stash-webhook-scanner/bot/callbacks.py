"""内联键盘回调处理器 — 菜单导航、删除流程、归类流程。"""

import logging
import threading

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from config import Config
from bot.utils import safe_edit_text, safe_delete_message, fmt_file_size

logger = logging.getLogger(__name__)

_MAIN_MENU_TEXT = "🤖 <b>欢迎使用 Stash 管理助手！</b>\n\n请选择功能："


def _back_to_main_keyboard():
    """返回主菜单 + 关闭 按钮。"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬅️ 返回主菜单", callback_data="menu_main"),
            InlineKeyboardButton("❌ 关闭", callback_data="menu_close"),
        ]
    ])


# ─────────────── 菜单回调 ───────────────

async def _on_menu_main(query):
    """返回主菜单。"""
    from bot.app import _main_menu_keyboard
    await safe_edit_text(
        query, _MAIN_MENU_TEXT,
        reply_markup=_main_menu_keyboard(), parse_mode="HTML",
    )


async def _on_menu_scrape(query):
    await safe_edit_text(
        query,
        "刮削场景\n\n"
        "请使用命令：\n/scrape 场景ID [jav|nonjav]\n\n"
        "例如：/scrape 12345 jav",
        reply_markup=_back_to_main_keyboard(),
        parse_mode="HTML",
    )


async def _on_menu_rescan(query):
    await safe_edit_text(
        query,
        "快速刮削\n\n"
        "请使用命令：\n/rescan 场景ID [jav|nonjav]\n\n"
        "例如：/rescan 12345 nonjav\n\n"
        "跳过已有元数据，仅重新抓取。",
        reply_markup=_back_to_main_keyboard(),
        parse_mode="HTML",
    )


async def _on_menu_code(query):
    await safe_edit_text(
        query,
        "🔎 番号搜索\n\n"
        "请使用命令：\n/code 番号\n\n"
        "例如：/code MIDA-708\n\n"
        "搜索 JavDB 获取详情、磁力链接、离线下载。",
        reply_markup=_back_to_main_keyboard(),
        parse_mode="HTML",
    )


async def _on_menu_status(query):
    """查询并展示 Stash 服务器状态 + 收藏库统计。"""
    from stash.client import StashClient
    from stash import query as Q

    try:
        client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)

        # 基础信息：版本、数据库
        data = await client.post(
            "query { systemStatus { databaseSchema } version { version hash } }", {}
        )
        # 收藏库统计：场景、演员、工作室、标签数量
        stats = await client.post(Q.LIBRARY_STATS, {})

        if data:
            sys_status = data.get("systemStatus", {})
            ver = data.get("version", {})
            out = [
                "📊 服务器状态",
                "• Stash 版本：%s" % ver.get("version", "未知"),
                "• 构建哈希：%s" % ver.get("hash", "未知"),
                "• 数据库版本：%s" % sys_status.get("databaseSchema", "未知"),
                "• 连接地址：%s" % Config.STASH_URL,
            ]
            # 收藏库统计
            if stats:
                sc = stats.get("findScenes", {})
                pf = stats.get("findPerformers", {})
                st = stats.get("findStudios", {})
                tg = stats.get("findTags", {})
                out.append("")
                out.append("━━━ 收藏库统计 ━━━")
                out.append("• 📹 场景：%s" % sc.get("count", "未知"))
                out.append("• 🎭 演员：%s" % pf.get("count", "未知"))
                out.append("• 🏢 工作室：%s" % st.get("count", "未知"))
                out.append("• 🏷️ 标签：%s" % tg.get("count", "未知"))
            text = "\n".join(out)
        else:
            text = "无法获取服务器状态，请检查 Stash 连接。"
    except Exception as e:
        text = "查询失败：%s" % e
    await safe_edit_text(query, text, reply_markup=_back_to_main_keyboard(), parse_mode="HTML")


async def _on_menu_delete(query):
    await safe_edit_text(
        query,
        "🗑️ 删除场景\n\n"
        "请使用命令：\n/delete 场景ID 或 /delete 番号\n\n"
        "例如：/delete 12345 或 /delete FPRE-020\n\n"
        "此操作将从 CD2 物理删除文件并从 Stash 移除场景记录。",
        reply_markup=_back_to_main_keyboard(),
        parse_mode="HTML",
    )


async def _on_menu_help(query):
    """展示帮助信息。"""
    from bot.app import _HELP_TEXT
    await safe_edit_text(query, _HELP_TEXT, reply_markup=_back_to_main_keyboard(), parse_mode="HTML")


async def _on_menu_mode(query):
    """响应主菜单的直链模式按钮。"""
    from bot.handlers import _get_current_mode, _build_mode_keyboard
    try:
        mode = await _get_current_mode()
        kb = _build_mode_keyboard(mode)
        await safe_edit_text(
            query,
            f"📡 <b>stash2alist 直链模式</b>\n\n当前: <code>{mode}</code>",
            reply_markup=kb, parse_mode="HTML",
        )
    except Exception as e:
        await safe_edit_text(query, f"❌ 查询失败: {e}", parse_mode="HTML")


async def _on_menu_close(query):
    await safe_delete_message(query)


# ─────────────── 归类流程回调 ───────────────

async def _on_menu_classify(query):
    """菜单中的文件归类按钮 — 显示规则选择。"""
    rules = Config.get_mover_rules()
    if not rules:
        await safe_edit_text(
            query, "当前没有配置归类规则。",
            reply_markup=_back_to_main_keyboard(), parse_mode="HTML",
        )
        return

    keyboard = []
    for i, r in enumerate(rules):
        name = r.get("name", "未命名")
        keyboard.append([
            InlineKeyboardButton("📂 归类: %s" % name, callback_data="mover_rule_%d" % i)
        ])
    keyboard.append([
        InlineKeyboardButton("⬅️ 返回主菜单", callback_data="menu_main"),
        InlineKeyboardButton("❌ 关闭", callback_data="menu_close"),
    ])

    await safe_edit_text(
        query,
        "<b>请选择要归类的目录：</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


async def _on_mover_cancel(query):
    await safe_delete_message(query)


# ─────────────── 删除流程回调 ───────────────

async def _on_delete_confirm(query, scene_id):
    """执行 CD2 物理删除 + Stash 场景移除。"""
    await safe_edit_text(query, "正在删除场景 %s…" % scene_id)

    from stash.client import StashClient
    from stash.delete import delete_scene
    from stash import query as Q
    from notify.builder import build_caption
    from scrape.detector import detect_japanese
    from scrape.code import extract_japanese_code

    try:
        client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)

        # 预先查询场景数据（删除后无法再查）
        scene_data = await client.post(Q.SCENE_FOR_NOTIFICATION, {"id": str(scene_id)})
        scene = scene_data.get("findScene") if scene_data else None

        result = await delete_scene(client, scene_id)

        if result.get("scene_destroyed"):
            caption = None
            if scene:
                # 检测 JAV
                files = scene.get("files") or []
                file_paths = []
                for f in files:
                    p = f.get("path", "")
                    if p:
                        for old_p, new_p in Config.PATH_PREFIX_MAP:
                            if p.startswith(old_p):
                                p = new_p + p[len(old_p):]
                                break
                        file_paths.append(p)

                is_japanese, _ = detect_japanese(file_paths, extract_japanese_code)
                base = Config.STASH_BASE_URL.rstrip("/")
                caption = await build_caption(
                    scene, is_japanese, client, base,
                    title_prefix='🗑️ <b>场景已删除</b>',
                )

                # 追加删除结果
                cd2_status = "已删除 %d 个" % result["files_deleted"]
                if result.get("files_failed"):
                    cd2_status += "，%d 个失败" % result["files_failed"]
                caption += (
                    "\n\n✅ <b>删除结果</b>"
                    "\n  • CD2 文件: %s"
                    "\n  • Stash 记录: 已移除" % cd2_status
                )
            else:
                caption = (
                    "✅ 场景 %s 已删除\n"
                    "  • CD2 文件: %d 个\n"
                    "  • Stash 记录: 已移除"
                ) % (scene_id, result.get("files_deleted", 0))

            await safe_edit_text(query, caption, parse_mode="HTML")
        else:
            await safe_edit_text(
                query,
                "删除场景 %s 失败\n\n%s" % (scene_id, result.get('scene_error', '未知错误')),
                parse_mode="HTML",
            )
    except Exception as e:
        logger.error("删除流程异常 scene=%s: %s", scene_id, e)
        await safe_edit_text(
            query, "删除流程异常：%s" % e, parse_mode="HTML",
        )


async def _on_soft_delete_confirm(query, scene_id):
    """TG 按钮「✅ 确定删除」→ CD2 物理删文件。"""
    from stash.soft_delete import confirm_delete_files, pop_pending

    await safe_edit_text(query, "正在物理删除文件…")

    try:
        result = await confirm_delete_files(scene_id)
        if "error" in result:
            await safe_edit_text(query, "❌ %s" % result["error"], parse_mode="HTML")
            return

        lines = ["🗑️ <b>已物理删除</b>"]
        if result.get("title"):
            lines.append("📝 <b>标题:</b> %s" % result["title"])
        lines.append("✅ CD2 文件已删除: %d 个" % result["files_deleted"])
        if result.get("files_failed"):
            # 部分失败：保留 pending 记录，按钮保留可重试
            lines.append("❌ 失败: %s" % "、".join(
                "%s(%s)" % (f["path"], f["error"]) for f in result["files_failed"]
            ))
            keyboard = [[
                InlineKeyboardButton("✅ 重试删除", callback_data="sdel_confirm_%s" % scene_id),
                InlineKeyboardButton("♻️ 恢复", callback_data="sdel_restore_%s" % scene_id),
            ]]
            await safe_edit_text(
                query, "\n".join(lines), parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            pop_pending(scene_id)
            await safe_edit_text(query, "\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.error("物理删除异常 scene=%s: %s", scene_id, e)
        await safe_edit_text(query, "❌ 物理删除异常：%s" % e, parse_mode="HTML")


async def _on_soft_delete_restore(query, scene_id):
    """TG 按钮「♻️ 恢复」→ 快速扫描原路径重新入库。"""
    from stash.soft_delete import restore_scene, pop_pending

    await safe_edit_text(query, "正在提交恢复扫描…")

    try:
        result = await restore_scene(scene_id)
        if "error" in result:
            await safe_edit_text(query, "❌ %s" % result["error"], parse_mode="HTML")
            return

        pop_pending(scene_id)
        lines = ["♻️ <b>已恢复</b>"]
        if result.get("title"):
            lines.append("📝 <b>标题:</b> %s" % result["title"])
        lines.append("🚀 恢复扫描任务 #%s 已提交" % result["job_id"])
        if result.get("new_scene_id"):
            lines.append("🆕 新场景: %s" % result["new_scene_id"])
        if result.get("meta_restored"):
            lines.append("✅ 元数据已还原")
        else:
            lines.append("⚠️ 元数据回写失败/跳过（可用 /scrape 重新刮削）")
        await safe_edit_text(query, "\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.error("恢复异常 scene=%s: %s", scene_id, e)
        await safe_edit_text(query, "❌ 恢复异常：%s" % e, parse_mode="HTML")


async def _on_sprite_regen(query, scene_id):
    """TG 按钮「🔄 重新生成 Sprite」→ 提交任务后立即返回，后台轮询。"""
    await safe_edit_text(query, "⏳ 正在重新生成 Sprite（覆盖），完成后将自动通知…")

    try:
        from stash.client import StashClient
        from stash.scanner import get_job_status

        client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)
        mutation = """
        mutation RegenSprite($input: GenerateMetadataInput!) {
          metadataGenerate(input: $input)
        }
        """
        data = await client.post(mutation, {
            "input": {"sprites": True, "overwrite": True, "sceneIDs": [str(scene_id)]},
        })
        if not data:
            await safe_edit_text(query, "❌ 生成任务提交失败。", parse_mode="HTML")
            return
        job_id = data["metadataGenerate"]
        logger.info("sprite 重新生成 scene=%s job=%s", scene_id, job_id)

        # 保存消息句柄供后台轮询回调编辑
        chat_id = query.message.chat_id if query.message else None
        msg_id = query.message.message_id if query.message else None
        bot = query.bot

    except Exception as e:
        logger.error("sprite 重生成提交异常 scene=%s: %s", scene_id, e)
        await safe_edit_text(query, "❌ 异常：%s" % e, parse_mode="HTML")
        return

    # 后台轮询，不阻塞 bot 事件循环
    import asyncio

    async def _poll_sprite():
        import asyncio
        status = None
        try:
            for _ in range(120):  # 最多等 10 分钟
                st = await get_job_status(client, job_id)
                status = (st or {}).get("status")
                if status in ("FINISHED", "FAILED", "CANCELLED"):
                    break
                await asyncio.sleep(5)

            if status == "FINISHED":
                text = "✅ Sprite 重新生成完成（任务 #%s）。\n刷新客户端即可看到新帧间隔。" % job_id
            else:
                text = "⚠️ 生成任务 #%s 状态: %s（可稍后重试）" % (job_id, status)
        except Exception as e:
            logger.error("sprite 轮询异常 scene=%s: %s", scene_id, e)
            text = "❌ 轮询异常：%s" % e

        try:
            if bot and chat_id and msg_id:
                await bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, parse_mode="HTML")
        except Exception as e:
            logger.warning("sprite 通知编辑失败: %s", e)

    asyncio.create_task(_poll_sprite())


async def _on_delete_cancel(query):
    await safe_delete_message(query)


async def _on_delete_pick(query, scene_id):
    """用户从编号列表中选择了一个场景，展示确认弹窗。"""
    from stash.client import StashClient
    from stash import query as Q

    client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)
    data = await client.post(Q.SCENE_FOR_NOTIFICATION, {"id": str(scene_id)})
    if not data or not data.get("findScene"):
        await safe_edit_text(query, "无法获取场景信息。", parse_mode="HTML")
        return
    scene = data["findScene"]
    confirm_text = await _build_delete_confirm_text(scene, scene_id)
    keyboard = [[
        InlineKeyboardButton("✅ 确认删除", callback_data="del_confirm_%s" % scene_id),
        InlineKeyboardButton("❌ 取消", callback_data="del_cancel"),
    ]]
    await safe_edit_text(query, confirm_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def _build_delete_confirm_text(scene, scene_id, is_japanese=None):
    """构建删除确认消息文本（复用 build_caption 格式，追加文件详情与操作警告）。"""
    from stash.client import StashClient
    from notify.builder import build_caption
    base = Config.STASH_BASE_URL.rstrip("/")
    client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)

    # ── 自动检测 JAV / Non-JAV ──
    if is_japanese is None:
        tags = scene.get("tags") or []
        is_japanese = any(t.get("name") == "JAV" for t in tags)
        if not is_japanese and not tags and scene.get("code"):
            is_japanese = True

    # 复用 build_caption 生成主内容（标题改为删除确认）
    caption = await build_caption(
        scene, is_japanese, client, base,
        title_prefix='🗑️ <b>确认删除场景？</b>',
    )

    # 追加文件详情（路径 + 大小）
    files = scene.get("files") or []
    file_lines = []
    for f in files:
        file_lines.append(fmt_file_size(f))
    files_section = "\n📁 <b>文件:</b> %d 个\n%s" % (len(files), "\n".join(file_lines))

    # 追加操作警告
    warning = (
        "\n\n此操作将：\n"
        "1. 从 CloudDrive2 物理删除上述文件\n"
        "2. 从 Stash 移除场景记录\n\n"
        "此操作不可撤销。"
    )

    return caption + files_section + warning
# ─────────────── 总路由 ───────────────

CALLBACK_ROUTES = {
    "menu_main": _on_menu_main,
    "menu_scrape": _on_menu_scrape,
    "menu_rescan": _on_menu_rescan,
    "menu_code": _on_menu_code,
    "menu_status": _on_menu_status,
    "menu_delete": _on_menu_delete,
    "menu_help": _on_menu_help,
    "menu_mode": _on_menu_mode,
    "menu_close": _on_menu_close,
    "menu_archive_task": _on_menu_classify,
    "del_cancel": _on_delete_cancel,
    "mover_cancel": _on_mover_cancel,
}


async def on_button_click(update, context: ContextTypes.DEFAULT_TYPE):
    """处理所有内联键盘按钮点击。"""
    query = update.callback_query
    await query.answer()
    data = query.data

    # 精确匹配路由
    if data in CALLBACK_ROUTES:
        await CALLBACK_ROUTES[data](query)
        return

    # 前缀匹配路由
    if data.startswith("javdb_pick_"):
        movie_id = data[len("javdb_pick_"):]
        from bot.javdb_search import handle_javdb_detail
        await handle_javdb_detail(query, movie_id)

    elif data.startswith("del_confirm_"):
        scene_id = data[len("del_confirm_"):]
        await _on_delete_confirm(query, scene_id)

    elif data.startswith("sdel_confirm_"):
        scene_id = data[len("sdel_confirm_"):]
        await _on_soft_delete_confirm(query, scene_id)

    elif data.startswith("sdel_restore_"):
        scene_id = data[len("sdel_restore_"):]
        await _on_soft_delete_restore(query, scene_id)

    elif data.startswith("sprite_regen_"):
        scene_id = data[len("sprite_regen_"):]
        await _on_sprite_regen(query, scene_id)

    elif data.startswith("del_pick_"):
        scene_id = data[len("del_pick_"):]
        await _on_delete_pick(query, scene_id)

    elif data.startswith("mag_page_"):
        from bot.javdb_search import handle_magnet_page
        parts = data[len("mag_page_"):].rsplit("_", 1)
        if len(parts) == 2:
            movie_id, page_str = parts
            try:
                await handle_magnet_page(query, movie_id, int(page_str))
            except ValueError:
                pass

    elif data.startswith("mag_add_"):
        from bot.javdb_search import handle_magnet_add
        parts = data[len("mag_add_"):].rsplit("_", 1)
        if len(parts) == 2:
            movie_id, idx_str = parts
            try:
                idx = int(idx_str)
                await handle_magnet_add(query, movie_id, idx)
            except ValueError:
                pass

    elif data.startswith("mag_dir_"):
        from bot.javdb_search import handle_magnet_dir_pick
        parts = data[len("mag_dir_"):].rsplit("_", 2)
        if len(parts) == 3:
            movie_id, idx_str, dir_idx_str = parts
            try:
                idx = int(idx_str)
                dir_idx = int(dir_idx_str)
                mover = context.application.bot_data.get("mover_handler")
                await handle_magnet_dir_pick(
                    query, movie_id, idx, dir_idx,
                    bot=context.bot, mover_handler=mover,
                )
            except ValueError:
                pass

    elif data.startswith("mon_check_"):
        from bot.javdb_search import handle_monitor_check
        try:
            msg_id = int(data[len("mon_check_"):])
            await handle_monitor_check(query, msg_id)
        except ValueError:
            pass

    elif data.startswith("mon_close_"):
        from bot.javdb_search import handle_monitor_close
        try:
            msg_id = int(data[len("mon_close_"):])
            await handle_monitor_close(query, msg_id)
        except ValueError:
            pass

    elif data.startswith("mode:"):
        await _handle_mode_switch(query, data)

    elif data.startswith("mover_rule_"):
        try:
            rule_idx = int(data[len("mover_rule_"):])
        except ValueError:
            await query.answer("无效选择")
            return
        rules = Config.get_mover_rules()
        if rule_idx < 0 or rule_idx >= len(rules):
            await query.answer("无效规则")
            return
        rule = rules[rule_idx]
        name = rule.get("name", "未命名")
        mover = context.application.bot_data.get("mover_handler")
        if mover is None:
            await safe_edit_text(
                query, "搬移模块未初始化。", parse_mode="HTML",
            )
            return
        try:
            await query.edit_message_text(
                "%s 归类已启动，正在后台执行…" % name,
                parse_mode="HTML",
            )
        except BadRequest:
            pass

        if Config.CLASSIFY_START_AUTO_DELETE_DELAY > 0:
            from bot.javdb_search_state import _schedule_auto_delete
            _schedule_auto_delete(
                context.bot,
                query.message.chat_id,
                query.message.message_id,
                Config.CLASSIFY_START_AUTO_DELETE_DELAY,
            )

        threading.Thread(
            target=mover._do_traverse_and_move,
            kwargs={"rule_indices": [rule_idx], "chat_id": query.message.chat_id},
            daemon=True,
        ).start()

# ─────────────── stash2alist 模式切换回调 ───────────────

async def _handle_mode_switch(query, data: str):
    """处理模式切换按钮点击。"""
    from bot.handlers import _get_current_mode, _switch_mode, _build_mode_keyboard
    from config import Config

    if data == "mode:refresh":
        try:
            mode = await _get_current_mode()
            kb = _build_mode_keyboard(mode)
            await safe_edit_text(
                query,
                f"📡 <b>stash2alist 直链模式</b>\n\n当前: <code>{mode}</code>",
                reply_markup=kb, parse_mode="HTML",
            )
        except Exception as e:
            await query.answer(f"查询失败: {e}")
        return

    if data.startswith("mode:switch:"):
        target = data[len("mode:switch:"):]
        if target not in ("alist", "cd2"):
            await query.answer("无效模式")
            return

        await safe_edit_text(query, f"⏳ 正在切换到 {target} 模式...")
        try:
            new_mode = await _switch_mode(target)
            kb = _build_mode_keyboard(new_mode)
            await safe_edit_text(
                query,
                f"✅ 已切换为 <code>{new_mode}</code> 模式",
                reply_markup=kb, parse_mode="HTML",
            )
        except Exception as e:
            await query.answer(f"切换失败: {e}")
        return

    # mode:noop -> 当前模式按钮，无操作
    await query.answer("当前已是此模式")