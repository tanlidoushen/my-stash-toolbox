"""Telegram 机器人入口模块。

负责构建 Application、注册命令处理器、自动消息响应。
采用 TranscriberBot 风格：简洁的 ApplicationBuilder + run_polling。
"""

import asyncio
import logging

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand, ReactionTypeEmoji,
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters,
)
from telegram.error import NetworkError, TimedOut

from config import Config
from bot.callbacks import on_button_click

logger = logging.getLogger(__name__)

# ?? python-telegram-bot ?? httpx ????
logging.getLogger("httpx").setLevel(logging.WARNING)


# ─────────────── 启动回调 ───────────────

async def post_init(application: Application) -> None:
    """启动时自动注册左下角 menu 命令列表，并初始化 mover_handler 的 bot/loop 引用。"""
    menu_commands = [
        BotCommand("start", "打开主菜单"),
        BotCommand("help", "查看帮助信息"),
        BotCommand("scrape", "刮削指定场景 — /scrape 场景ID [jav|nonjav]"),
        BotCommand("rescan", "快速刮削 — /rescan 场景ID [jav|nonjav]"),
        BotCommand("delete", "删除指定场景 — /delete 场景ID或番号"),
        BotCommand("archive_task", "归类移动 — /archive_task"),
        BotCommand("mode", "查看/切换 stash2alist 代理模式"),
    ]
    try:
        await application.bot.set_my_commands(menu_commands)
        logger.info("✅ 左下角 menu 快捷菜单已同步")
    except Exception as e:
        logger.warning("menu 注册失败: %s", e)

    # 将正在运行的事件循环和 bot 实例存入 mover_handler，供后台线程异步发消息
    mover_handler = application.bot_data.get("mover_handler")
    if mover_handler:
        mover_handler._bot = application.bot
        mover_handler._loop = asyncio.get_running_loop()
        logger.info("✅ mover_handler bot/loop 引用已设置")


# ─────────────── 命令处理器 ───────────────

def _main_menu_keyboard():
    """构建主菜单内联键盘。"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 刮削场景", callback_data="menu_scrape"),
            InlineKeyboardButton("⚡ 快速刮削", callback_data="menu_rescan"),
        ],
        [
            InlineKeyboardButton("🔎 番号搜索", callback_data="menu_code"),
            InlineKeyboardButton("🗑️ 删除场景", callback_data="menu_delete"),
        ],
        [
            InlineKeyboardButton("📦 文件归类", callback_data="menu_archive_task"),
            InlineKeyboardButton("🖥️ 服务器状态", callback_data="menu_status"),
        ],
        [
            InlineKeyboardButton("📡 直链模式", callback_data="menu_mode"),
            InlineKeyboardButton("❓ 帮助", callback_data="menu_help"),
        ],
        [
            InlineKeyboardButton("❌ 关闭", callback_data="menu_close"),
        ],
    ])


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """响应 /start，弹出内联键盘主菜单。"""
    await update.message.reply_text(
        "🤖 <b>欢迎使用 Stash 管理助手！</b>\n\n请选择功能：",
        reply_markup=_main_menu_keyboard(),
        parse_mode="HTML",
    )


_HELP_TEXT = (
    "Stash 管理助手 — 帮助\n\n"
    "可用命令：\n"
    "· /start — 打开交互主菜单\n"
    "· /help — 查看本帮助信息\n"
    "· /scrape 场景ID [jav|nonjav] — 对指定场景执行刮削处理（可选指定类型）\n"
    "· /rescan 场景ID [jav|nonjav] — 快速重新刮削（跳过已有的元数据）\n"
    "· /delete 场景ID — 从 CloudDrive2 物理删除文件并从 Stash 移除记录\n"
    "· /archive_task — 手动触发文件归类移动\n"
    "· /mode — 查看/切换 stash2alist 代理模式（Alist / CloudDrive2）\n\n"
    "也可点击左下角 menu 按钮快速选择。"
)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """响应 /help，发送帮助文本。"""
    await update.message.reply_text(_HELP_TEXT, parse_mode="HTML")


async def cmd_rescan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """响应 /rescan <场景ID>，快速刮削。"""
    from bot.handlers import handle_rescan_command
    await handle_rescan_command(update, context)


async def cmd_scrape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """响应 /scrape <场景ID>，启动场景刮削流水线。"""
    from bot.handlers import handle_scrape_command
    await handle_scrape_command(update, context)


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """响应 /delete <场景ID>，弹出确认后 CD2 + Stash 删除。"""
    from bot.handlers import handle_delete_command
    await handle_delete_command(update, context)


async def cmd_classify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """响应 /archive_task，弹出归类规则选择菜单。"""
    from bot.handlers import handle_classify_command
    await handle_classify_command(update, context)


async def cmd_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """响应 /mode，查看/切换 stash2alist 代理模式。"""
    from bot.handlers import cmd_mode as _cmd_mode
    await _cmd_mode(update, context)


# ─────────────── 消息自动响应 ───────────────

async def auto_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """对来自所有者的消息自动添加表情反应。"""
    try:
        await update.message.set_reaction(
            reaction=[ReactionTypeEmoji("\U0001f44d")]
        )
        logger.debug("为消息 %d 添加了反应", update.message.message_id)
    except Exception as e:
        logger.debug("设置消息反应失败: %s", e)


# ─────────────── 异常统一处理 ───────────────

async def handle_telegram_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram 异常统一处理：网络抖动只记一行 WARNING，其余错误才记 ERROR 堆栈。"""
    error = context.error
    if isinstance(error, (NetworkError, TimedOut)):
        logger.warning("Telegram 网络异常（PTB 自动重试中）: %s", error)
        return
    logger.error("Telegram 处理异常: %s", error, exc_info=error)


# ─────────────── 应用构建 ───────────────

def build_application(mover_handler=None):
    """构建并返回配置好的 Application 实例。"""
    builder = Application.builder().token(Config.TG_BOT_TOKEN)
    builder.post_init(post_init)
    app = builder.build()
    app.add_error_handler(handle_telegram_error)

    # 将 mover_handler 存入 bot_data，供回调/post_init 和其他模块访问
    if mover_handler is not None:
        app.bot_data["mover_handler"] = mover_handler

    owner_filter = filters.User(Config.TG_OWNER_ID)

    app.add_handler(CommandHandler("start", cmd_start, filters=owner_filter))
    app.add_handler(CommandHandler("help", cmd_help, filters=owner_filter))
    app.add_handler(CommandHandler("scrape", cmd_scrape, filters=owner_filter))
    app.add_handler(CommandHandler("rescan", cmd_rescan, filters=owner_filter))
    app.add_handler(CommandHandler("delete", cmd_delete, filters=owner_filter))
    app.add_handler(CommandHandler("archive_task", cmd_classify, filters=owner_filter))
    app.add_handler(CommandHandler("mode", cmd_mode, filters=owner_filter))
    # 消息自动响应：对所有者的消息添加反应（低优先级，不干扰命令路由）
    app.add_handler(
        MessageHandler(owner_filter & filters.TEXT, auto_reaction),
        group=-1,
    )
    app.add_handler(CallbackQueryHandler(on_button_click))

    return app


def run_bot(mover_handler=None):
    """启动机器人 polling，基于 PTB 内置重连机制。

    兼容主线程/后台线程：不能直接用 app.run_polling()，
    它内部调用 loop.add_signal_handler() 只能在主线程使用；
    本项目 bot 运行在 daemon 后台线程中（Linux 下会抛
    RuntimeError: set_wakeup_fd only works in main thread）。
    改用 initialize + start_polling + start 手动启动并常驻事件循环。
    """
    logger.info("🤖 Telegram 机器人开始监听..")

    async def _run_forever_with_retry():
        while True:
            try:
                app = build_application(mover_handler=mover_handler)
                await app.initialize()
                await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
                await app.start()
                while True:
                    await asyncio.sleep(3600)
            except (NetworkError, TimedOut, OSError) as e:
                logger.warning(f"🌐 网络连接异常: {e}, 10秒后重连...")
                try:
                    await app.stop()
                    await app.shutdown()
                except Exception:
                    pass
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"💥 Bot 异常崩溃: {e}, 5秒后重启...")
                try:
                    await app.stop()
                    await app.shutdown()
                except Exception:
                    pass
                await asyncio.sleep(5)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_forever_with_retry())
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        try:
            loop.close()
        except Exception:
            pass
