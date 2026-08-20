"""命令处理器 — /scrape 等命令的具体逻辑。"""

import asyncio
import logging
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import Config
from stash.client import StashClient
from stash import query as Q
from bot.utils import fmt_file_size
from bot.callbacks import _build_delete_confirm_text
from scrape.code import extract_japanese_code
from scrape.detector import detect_japanese
from notify.telegram import send_notification

logger = logging.getLogger(__name__)


def parse_scene_args(cmd, args):
    """解析 /scrape|/rescan 参数，支持类型写在 ID 前或后。

    类型大小写不敏感，jav / nonjav / nojav / non-jav 均可。
    返回 (scene_id, forced_type, error)：
      forced_type = True(JAV) / False(Non-JAV) / None(自动)。
    """
    if not args:
        return None, None, (
            "请提供场景 ID。\n用法：/%s 场景ID [jav|nonjav]\n"
            "例如：/%s 12345 jav" % (cmd, cmd)
        )

    if len(args) > 2:
        return None, None, (
            "参数过多。\n用法：/%s 场景ID [jav|nonjav]\n"
            "例如：/%s 12345 jav" % (cmd, cmd)
        )

    scene_id_str = None
    forced_type = None
    for arg in args:
        token = arg.strip().lower().replace("-", "").replace("_", "")
        if token in ("jav", "nonjav", "nojav"):
            if forced_type is not None:
                return None, None, "类型参数重复。\n用法：/%s 场景ID [jav|nonjav]" % cmd
            forced_type = token == "jav"
        elif arg.isdigit():
            if scene_id_str is not None:
                return None, None, "场景 ID 重复。\n用法：/%s 场景ID [jav|nonjav]" % cmd
            scene_id_str = arg
        else:
            return None, None, (
                "无法识别的参数 <code>%s</code>。\n用法：/%s 场景ID [jav|nonjav]\n"
                "例如：/%s 12345 jav" % (arg, cmd, cmd)
            )

    if scene_id_str is None:
        return None, None, (
            "请提供场景 ID。\n用法：/%s 场景ID [jav|nonjav]\n"
            "例如：/%s 12345 jav" % (cmd, cmd)
        )

    return int(scene_id_str), forced_type, None


# ─────────────── 后台刮削任务 ───────────────

async def _bg_scrape(scene_id, file_path, status_msg, context, forced_type=None):
    """后台异步执行刮削，完成后删除进度消息，发送带图通知。"""
    try:
        from scrape.pipeline import run_scans
        await run_scans(Config.STASH_URL, [file_path], skip_notification=True, forced_type=forced_type)
        try:
            await status_msg.delete()
        except Exception:
            pass
        if forced_type is None:
            is_japanese, _ = detect_japanese([file_path], extract_japanese_code)
        else:
            is_japanese = forced_type
        client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)
        await send_notification(client, scene_id, is_japanese, target_chat_id=status_msg.chat_id, bot=context.bot)
    except Exception as e:
        logger.error("后台刮削异常 scene=%d: %s", scene_id, e)
        try:
            await status_msg.edit_text(
                "场景 %d 刮削异常: %s\n文件: %s" % (scene_id, e, file_path),
                parse_mode="HTML",
            )
        except Exception:
            pass


async def _bg_rescan(client, scene_id, file_path, status_msg, context, forced_type=None):
    """后台异步执行快速刮削，完成后删除进度消息，发送带图通知。"""
    try:
        from scrape.pipeline import run_scrape_only
        await run_scrape_only(client, scene_id, file_path, skip_notification=True, forced_type=forced_type)
        try:
            await status_msg.delete()
        except Exception:
            pass
        if forced_type is None:
            is_japanese, _ = detect_japanese([file_path], extract_japanese_code)
        else:
            is_japanese = forced_type
        await send_notification(client, scene_id, is_japanese, target_chat_id=status_msg.chat_id, bot=context.bot)
    except Exception as e:
        logger.error("后台快速刮削异常 scene=%d: %s", scene_id, e)
        try:
            await status_msg.edit_text(
                "场景 %d 快速刮削异常: %s\n文件: %s" % (scene_id, e, file_path),
                parse_mode="HTML",
            )
        except Exception:
            pass


# ─────────────── /scrape 命令 ───────────────

async def handle_scrape_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """解析 /scrape <场景ID> [jav|nonjav]，取文件路径后交给 run_scans 流水线（异步后台）。"""
    chat_id = update.effective_chat.id

    scene_id, forced_type, err = parse_scene_args("scrape", context.args)
    if err:
        await update.message.reply_text(err, parse_mode="HTML")
        return

    client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)

    data = await client.post(Q.SCENE_FOR_NOTIFICATION, {"id": str(scene_id)})
    if not data:
        await update.message.reply_text("无法查询场景 %d，请检查 Stash 连接。" % scene_id)
        return

    scene = data.get("findScene")
    if not scene:
        await update.message.reply_text("未找到场景 %d。" % scene_id)
        return

    files = scene.get("files", [])
    if not files:
        await update.message.reply_text("场景 %d 没有关联文件，无法刮削。" % scene_id)
        return

    file_path = files[0].get("path", "")
    if not file_path:
        await update.message.reply_text("场景 %d 的文件路径为空。" % scene_id)
        return

    # 路径前缀替换
    for old, new in Config.PATH_PREFIX_MAP:
        if file_path.startswith(old):
            file_path = new + file_path[len(old):]
            break

    type_label = {True: "JAV", False: "Non-JAV"}.get(forced_type, "自动")
    status_msg = await update.message.reply_text(
        "场景 %d 已加入刮削队列（%s）\n正在后台处理…" % (scene_id, type_label)
    )
    asyncio.create_task(_bg_scrape(scene_id, file_path, status_msg, context, forced_type))


# ─────────────── /rescan 命令 ───────────────

async def handle_rescan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """解析 /rescan <场景ID> [jav|nonjav]，快速刮削。"""
    chat_id = update.effective_chat.id

    scene_id, forced_type, err = parse_scene_args("rescan", context.args)
    if err:
        await update.message.reply_text(err, parse_mode="HTML")
        return

    client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)

    data = await client.post(Q.SCENE_FOR_NOTIFICATION, {"id": str(scene_id)})
    if not data or not data.get("findScene"):
        await update.message.reply_text("未找到场景 %d。" % scene_id)
        return

    scene = data["findScene"]
    files = scene.get("files", [])
    if not files:
        await update.message.reply_text("场景 %d 没有关联文件。" % scene_id)
        return

    file_path = files[0].get("path", "")
    if not file_path:
        await update.message.reply_text("场景 %d 的文件路径为空。" % scene_id)
        return

    for old, new in Config.PATH_PREFIX_MAP:
        if file_path.startswith(old):
            file_path = new + file_path[len(old):]
            break

    type_label = {True: "JAV", False: "Non-JAV"}.get(forced_type, "自动")
    status_msg = await update.message.reply_text(
        "场景 %d 已加入快速刮削队列（%s）\n正在后台处理…" % (scene_id, type_label)
    )
    asyncio.create_task(_bg_rescan(client, scene_id, file_path, status_msg, context, forced_type))


# ─────────────── /delete 命令 ───────────────

async def handle_delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """解析 /delete <场景ID 或 番号>，弹出确认后删除。"""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "请提供场景 ID 或番号。\n用法：/delete 场景ID\n"
            "例如：/delete 12345 或 /delete FPRE-020",
            parse_mode="HTML",
        )
        return

    query_arg = " ".join(context.args)
    client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)

    if query_arg.isdigit():
        scene_id = int(query_arg)
        data = await client.post(Q.SCENE_FOR_NOTIFICATION, {"id": str(scene_id)})
        if not data or not data.get("findScene"):
            await update.message.reply_text("未找到场景 %d。" % scene_id)
            return
        scene = data["findScene"]
        await _show_delete_confirm(update, scene, scene_id)
        return

    # 文本 → 归一化番号格式后搜索
    m = re.match(r'^([a-zA-Z]+)[\s\-]*(\d+)$', query_arg)
    if m:
        normalized = "%s-%s" % (m.group(1).upper(), m.group(2))
        if normalized != query_arg:
            query_arg = normalized

    data = await client.post(Q.FIND_SCENES_BY_CODE, {
        "filter": {"code": {"value": query_arg, "modifier": "EQUALS"}}
    })
    if not data:
        await update.message.reply_text("查询番号 %s 失败。" % query_arg)
        return

    scenes_data = data.get("findScenes", {})
    scenes = scenes_data.get("scenes", [])
    count = scenes_data.get("count", 0)

    if count == 0:
        await update.message.reply_text(
            '未找到番号为 <code>%s</code> 的场景。' % query_arg, parse_mode="HTML"
        )
        return

    if count == 1:
        await _show_delete_confirm(update, scenes[0], scenes[0]["id"])
        return

    # 多个匹配 → 编号列表 + 选择按钮
    base = Config.STASH_BASE_URL.rstrip("/")
    list_lines = ['找到 %d 个番号为 <code>%s</code> 的场景：\n' % (count, query_arg)]
    pick_buttons = []
    row = []
    for idx, s in enumerate(scenes, 1):
        sid = s["id"]
        stitle = s.get("title") or "(无标题)"
        sdate = s.get("date") or ""
        sdate_str = " [%s]" % sdate if sdate else ""
        list_lines.append(
            '%d. <a href="%s/scenes/%d">%s</a>%s' % (idx, base, sid, stitle, sdate_str)
        )
        row.append(
            InlineKeyboardButton("%d. %d" % (idx, sid), callback_data="del_pick_%d" % sid)
        )
        if len(row) == 3:
            pick_buttons.append(row)
            row = []
    if row:
        pick_buttons.append(row)
    pick_buttons.append([InlineKeyboardButton("❌ 取消", callback_data="del_cancel")])

    list_lines.append("\n请选择要删除的场景：")

    await update.message.reply_text(
        "\n".join(list_lines),
        reply_markup=InlineKeyboardMarkup(pick_buttons),
        parse_mode="HTML",
    )


async def _show_delete_confirm(update: Update, scene, scene_id):
    """展示删除确认弹窗。"""
    confirm_text = await _build_delete_confirm_text(scene, scene_id)

    keyboard = [[
        InlineKeyboardButton("✅ 确认删除", callback_data="del_confirm_%d" % scene_id),
        InlineKeyboardButton("❌ 取消", callback_data="del_cancel"),
    ]]
    await update.message.reply_text(
        confirm_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# ─────────────── /archive_task 文件归类命令 ───────────────

async def handle_classify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """响应 /archive_task，弹出归类规则选择菜单。"""
    rules = Config.get_mover_rules()
    if not rules:
        await update.message.reply_text("当前没有配置归类规则。")
        return

    keyboard = []
    for i, r in enumerate(rules):
        name = r.get("name", "未命名")
        keyboard.append([
            InlineKeyboardButton("📂 归类: %s" % name, callback_data="mover_rule_%d" % i)
        ])

    keyboard.append([
        InlineKeyboardButton("❌ 取消", callback_data="mover_cancel"),
    ])

    await update.message.reply_text(
        "<b>请选择要归类的目录：</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )

# ─────────────── /mode stash2alist 模式切换 ───────────────

import httpx

async def _get_current_mode() -> str:
    """查询 stash2alist 当前直链模式。"""
    url = Config.STASH2ALIST_MODE_API
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data.get("mode", "unknown")

async def _switch_mode(target: str) -> str:
    """切换 stash2alist 直链模式。"""
    url = Config.STASH2ALIST_MODE_API
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.post(url, json={"mode": target})
        resp.raise_for_status()
        data = resp.json()
        return data.get("mode", "unknown")

def _build_mode_keyboard(current_mode: str):
    """构建模式切换内联键盘。"""
    keyboard = []
    row = []
    for mode, label in [("alist", "Alist"), ("cd2", "CD2")]:
        if mode == current_mode:
            row.append(InlineKeyboardButton(f"✅ {label}", callback_data="mode:noop"))
        else:
            row.append(InlineKeyboardButton(f"🔄 切换到 {label}", callback_data=f"mode:switch:{mode}"))
    keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔄 刷新", callback_data="mode:refresh")])
    return InlineKeyboardMarkup(keyboard)

async def cmd_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看/切换 stash2alist 直链模式。"""
    try:
        mode = await _get_current_mode()
        kb = _build_mode_keyboard(mode)
        await update.message.reply_text(
            f"📡 <b>stash2alist 直链模式</b>\n\n当前: <code>{mode}</code>",
            reply_markup=kb, parse_mode="HTML",
        )
    except Exception as e:
        logger.error("查询 stash2alist 模式失败: %s", e)
        await update.message.reply_text(
            "❌ 无法连接 stash2alist，请确认容器是否运行。\n"
            f"<code>{e}</code>",
            parse_mode="HTML",
        )


async def cmd_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/hash <场景ID> — 查询校验码采集库（checksums.db）返回各校验码。"""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "用法：/hash 场景ID\n例如：/hash 27717", parse_mode="HTML")
        return
    arg = context.args[0].strip()
    if not arg.isdigit():
        await update.message.reply_text("场景 ID 应为数字。", parse_mode="HTML")
        return

    from db import init_db, get_by_scene_id
    init_db()
    row = get_by_scene_id(arg)

    # 已有完整数据 → 直接发送
    if row and row.get("md5"):
        await _send_hash_result(update, arg, row)
        return

    # 需要阻塞操作 → 后台任务
    msg = await update.message.reply_text(
        "🔍 正在采集校验码（大文件 ed2k 需要一些时间），完成后将自动更新…",
        parse_mode="HTML")
    chat_id = msg.chat_id
    msg_id = msg.message_id
    bot = msg.bot

    async def _poll_hash():
        import asyncio
        from stash.client import StashClient
        from stash.checksum import collect_checksums, ensure_md5

        client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)
        try:
            # 1. 采集校验码（含 ed2k）
            if not row:
                result = await collect_checksums(client, arg)
                if "error" in result:
                    text = "❌ 采集失败：%s（场景不存在或无文件？）" % result["error"]
                    return await _safe_edit(bot, chat_id, msg_id, text)

            row = get_by_scene_id(arg)
            if not row:
                text = "❌ 采集完成但查询仍无记录（异常），请重试。"
                return await _safe_edit(bot, chat_id, msg_id, text)

            # 2. 缺 md5 → rescan 补算
            if not row.get("md5"):
                result = await ensure_md5(client, arg)
                if "error" in result:
                    text = "❌ 补 md5 失败：%s" % result["error"]
                    return await _safe_edit(bot, chat_id, msg_id, text)

            row = get_by_scene_id(arg)
            if not row:
                text = "❌ 采集完成但查询仍无记录（异常），请重试。"
                return await _safe_edit(bot, chat_id, msg_id, text)

            # 3. 构建完整结果
            text = _build_hash_text(arg, row)
            await _safe_edit(bot, chat_id, msg_id, text)

        except Exception as e:
            logger.error("hash 后台采集异常 scene=%s: %s", arg, e)
            await _safe_edit(bot, chat_id, msg_id, "❌ 采集异常：%s" % e)

    asyncio.create_task(_poll_hash())


async def _send_hash_result(update, scene_id, row):
    """直接发送校验码结果（已有数据，无需阻塞）。"""
    text = _build_hash_text(scene_id, row)
    import io
    import httpx
    from stash.client import StashClient

    client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)
    screenshot_url = None
    try:
        data = await client.post(
            "query Shot($id: ID!) { findScene(id: $id) { paths { screenshot } } }",
            {"id": scene_id},
        )
        scene = (data or {}).get("findScene") or {}
        paths = scene.get("paths") or {}
        screenshot_url = paths.get("screenshot")
    except Exception:
        pass

    if screenshot_url:
        text += "\n\n▶️ <a href=\"%s/scenes/%s\">查看原视频</a>" % (
            Config.STASH_BASE_URL.rstrip("/"), scene_id)
        try:
            async with httpx.AsyncClient(timeout=30, verify=False) as c:
                r = await c.get(screenshot_url)
                if r.status_code == 200:
                    from telegram import InputFile
                    from io import BytesIO
                    await update.message.reply_photo(
                        InputFile(BytesIO(r.content), filename="screenshot.jpg"),
                        caption=text, parse_mode="HTML")
                    return
        except Exception:
            pass

    await update.message.reply_text(text, parse_mode="HTML")


def _build_hash_text(scene_id, row):
    """构建校验码信息文本。"""
    base = Config.STASH_BASE_URL.rstrip("/")
    lines = []
    lines.append("🔑 <b>校验码信息</b>")
    lines.append('▶️ <a href="%s/scenes/%s">查看原视频</a>' % (base, scene_id))
    if row.get("region"):
        lines.append("🌐 <b>地区:</b> %s" % row["region"])
    if row.get("title"):
        lines.append("📝 <b>标题:</b> %s" % row["title"])
    if row.get("code"):
        lines.append("📀 <b>番号:</b> <code>%s</code>" % row["code"])
    lines.append("📁 <code>%s</code>" % row["cd2_path"])
    if row.get("file_size"):
        size = row["file_size"]
        if size >= 1024 ** 3:
            lines.append("💾 大小: %.2f GB" % (size / 1024 ** 3))
        elif size >= 1024 ** 2:
            lines.append("💾 大小: %.2f MB" % (size / 1024 ** 2))
        else:
            lines.append("💾 大小: %d B" % size)
    for key, label in (("ed2k", "🔑 ed2k"), ("sha1", "🔑 sha1"),
                       ("md5", "🔑 md5"), ("oshash", "🔑 oshash"),
                       ("phash", "🔑 phash")):
        v = row.get(key)
        if v:
            lines.append("%s: <code>%s</code>" % (label, v))
    for sid in (row.get("stash_ids") or []):
        ep = (sid.get("endpoint") or "").replace("https://", "").replace("/graphql", "")
        if sid.get("stash_id"):
            lines.append("🆔 %s: <code>%s</code>" % (ep, sid["stash_id"]))
    if row.get("updated_at"):
        lines.append("🕐 采集时间: %s" % row["updated_at"])
    return "\n".join(lines)


async def _safe_edit(bot, chat_id, msg_id, text):
    """安全地编辑消息（后台任务用）。"""
    try:
        await bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, parse_mode="HTML")
    except Exception as e:
        logger.warning("hash 编辑消息失败: %s", e)



async def cmd_sprite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/sprite <场景ID> — 查看场景 sprite(VTT) 信息；帧间隔偏离标准 ~10s（±3s 容差）时提供重新生成按钮。"""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "用法：/sprite 场景ID\n例如：/sprite 27689", parse_mode="HTML")
        return
    arg = context.args[0].strip()
    if not arg.isdigit():
        await update.message.reply_text("场景 ID 应为数字。", parse_mode="HTML")
        return

    import asyncio
    import re

    import httpx
    from stash.client import StashClient

    client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)
    query = """
    query SpriteInfo($id: ID!) {
      findScene(id: $id) { id title code date files { duration } paths { vtt sprite screenshot } }
    }
    """
    data = await client.post(query, {"id": arg})
    scene = (data or {}).get("findScene")
    if not scene:
        await update.message.reply_text("未找到场景 %s。" % arg, parse_mode="HTML")
        return

    vtt_url = (scene.get("paths") or {}).get("vtt")
    files = scene.get("files") or [{}]
    duration = files[0].get("duration")

    # 拉 VTT 解析帧数与间隔
    frames = None
    interval_ms = None
    if vtt_url:
        url = vtt_url if vtt_url.startswith("http") else Config.STASH_BASE_URL.rstrip("/") + vtt_url
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as c:
                resp = await c.get(url)
            times = re.findall(r"(\d+):(\d+):(\d+)\.(\d+)\s+-->", resp.text)
            frames = len(times)

            def _ms(t):
                return int(t[0]) * 3600000 + int(t[1]) * 60000 + int(t[2]) * 1000 + int(t[3])

            if frames > 1:
                interval_ms = _ms(times[1]) - _ms(times[0])
        except Exception as e:
            logger.warning("sprite 命令拉 VTT 失败 scene=%s: %s", arg, e)

    # 判定：标准 ~10s，容差 ±3s（模糊检测区间 7s~13s）
    if interval_ms is not None:
        abnormal = not (7000 <= interval_ms <= 13000)
    else:
        abnormal = True  # 无 VTT = 未生成

    base = Config.STASH_BASE_URL.rstrip("/")
    lines = ["🎞️ <b>Sprite 信息</b>"]
    lines.append('▶️ <a href="%s/scenes/%s">查看原视频</a>' % (base, arg))
    if scene.get("code"):
        lines.append("📀 <b>番号:</b> <code>%s</code>" % scene["code"])
    if scene.get("title"):
        lines.append("📝 <b>标题:</b> %s" % scene["title"][:60])
    if duration:
        lines.append("⏱️ <b>时长:</b> %.0f 分钟" % (duration / 60))
    lines.append("🖼️ <b>帧数:</b> %s" % (frames if frames is not None else "—"))
    if interval_ms is not None:
        lines.append("⏱️ <b>帧间隔:</b> %.1fs" % (interval_ms / 1000))
        if abnormal:
            lines.append("⚠️ <b>状态:</b> 异常（偏离标准 ~10s，±3s 容差）")
        else:
            lines.append("✅ <b>状态:</b> 正常（标准 ~10s）")
    else:
        lines.append("⚠️ <b>状态:</b> 无 VTT（sprite 未生成）")
    text = "\n".join(lines)

    reply_markup = None
    if abnormal:
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(
            "🔄 重新生成 Sprite", callback_data="sprite_regen_%s" % arg)]])

    # 图片消息（截图）+ 链接 + 按钮；无截图回退纯文本
    import io
    screenshot_url = (scene.get("paths") or {}).get("screenshot")
    img_data = None
    if screenshot_url:
        try:
            ss = screenshot_url if screenshot_url.startswith("http") else base + screenshot_url
            async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as c:
                resp = await c.get(ss)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                img_data = io.BytesIO(resp.content)
                img_data.name = "sprite.jpg"
        except Exception as e:
            logger.warning("sprite 命令截图下载失败 scene=%s: %s", arg, e)

    if img_data is not None:
        await update.message.reply_photo(
            photo=img_data, caption=text, parse_mode="HTML",
            reply_markup=reply_markup)
    else:
        await update.message.reply_text(
            text, parse_mode="HTML", reply_markup=reply_markup)

