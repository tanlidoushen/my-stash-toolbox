"""Flask 入口 —— 接收文件系统 Webhook 通知，同时触发 Stash 扫描 + 文件搬移。"""

import os
import logging
import sys
import threading

from flask import Flask, request, jsonify

# vendor（pycryptodome 等）——bind mount 目录，镜像重建不丢
import sys
_VENDOR = "/app/vendor"
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

from config import Config
from server.handler import FileNotifyHandler
from server import dedup
from mover.handler import FileMoveHandler as MoverHandler

# 根据 DEBUG 设置日志级别
_log_level = logging.DEBUG if Config.DEBUG else logging.INFO
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

app = Flask(__name__)

# Mute Werkzeug access logs
logging.getLogger("werkzeug").setLevel(logging.ERROR)

handler = FileNotifyHandler()
mover_handler = MoverHandler()

logger = logging.getLogger(__name__)


def _translate_action(action, source_file, destination_file):
    """Translate action to Chinese; distinguish move vs rename."""
    if action == "rename":
        src_dir = os.path.dirname(source_file)
        dst_dir = os.path.dirname(destination_file)
        return "移动" if src_dir != dst_dir else "重命名"
    return {"create": "创建", "delete": "删除"}.get(action, "未知操作")


@app.route("/file_notify", methods=["POST"])
def file_notify():
    data = request.json
    if not data:
        return jsonify({"状态": "错误", "消息": "无效的 JSON 数据"}), 400

    # 请求级去重
    raw_body = request.get_data()
    if dedup.is_duplicate_request(raw_body):
        logger.debug("收到重复通知，已忽略")
        return jsonify({"状态": "成功", "消息": "重复通知已忽略"}), 200

    items = data.get("data", [])

    # ── scanner 处理 ──
    notifications = []
    for item in items:
        src = item.get("source_file", "未知路径")
        dst = item.get("destination_file", "无")
        action_cn = _translate_action(item.get("action", "未知"), src, dst)
        notifications.append({
            "动作": action_cn,
            "类型": "目录" if item.get("is_dir") == "true" else "文件",
            "源路径": src,
            "目标路径": dst,
        })
        if action_cn in ("移动", "重命名") and dst != "无":
            handler.add_change(dst, source_path=src)
        elif action_cn == "创建":
            handler.add_change(src)

    if notifications:
        logger.debug("收到 %d 条通知：%s", len(notifications), notifications)

    # ── mover 处理（异步，不阻塞） ──
    if items:
        mover_handler.on_file_notify(items)

    return jsonify({"状态": "成功", "消息": "已接收文件系统通知"}), 200


# ────────────── 兼容 mover 原始路由 ──────────────

@app.route("/", methods=["GET", "POST"])
@app.route("/webhook", methods=["GET", "POST"])
def root_handler():
    """兼容扩展直接发往根路径的通知，根据 body 格式自动分流。"""
    if request.method == "GET":
        return jsonify({"status": "ok", "message": "Webhook server running"}), 200

    data = request.json
    if not data:
        return jsonify({"状态": "错误", "消息": "无效的 JSON 数据"}), 400

    raw_body = request.get_data()
    if dedup.is_duplicate_request(raw_body):
        logger.debug("收到重复通知，已忽略")
        return jsonify({"状态": "成功", "消息": "重复通知已忽略"}), 200

    # 判断类型：离线任务完成通知
    if data.get("fromCloudDrive") is True and data.get("event") == "offline":
        offline_file = data.get("body", {}).get("offlineFile", {})
        file_name = offline_file.get("name", "未知")
        parent_id = offline_file.get("parentId", "未知")
        logger.info("离线通知: event=%s | 文件=%s | parentId=%s", data.get("event"), file_name, parent_id)
        mover_handler.on_offline_notify(data)
        return jsonify({"状态": "成功", "消息": "离线通知已接收"}), 200

    # 否则作为文件变更通知处理
    items = data.get("data", [])
    for item in items:
        src = item.get("source_file", "未知路径")
        dst = item.get("destination_file", "无")
        action_cn = _translate_action(item.get("action", "未知"), src, dst)
        logger.info("通知: %s | %s → %s", action_cn, src, dst)

    if items:
        mover_handler.on_file_notify(items)

    return jsonify({"状态": "成功", "消息": "已接收通知"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "mover_enabled": mover_handler.enabled})


@app.route("/trigger", methods=["POST"])
def trigger():
    """手动触发搬移流水线（全部规则）。"""
    logger.info("收到手动触发请求")
    mover_handler._do_traverse_and_move(list(range(len(mover_handler.rules))))
    return jsonify({"状态": "成功", "消息": "搬移流水线已执行"})


@app.route("/api/delete_scene", methods=["POST"])
def api_delete_scene():
    """Yamby 删除联动：软删 Stash 记录 + TG 发确认按钮（确定删除/恢复）。

    请求: {"scene_id": "123"}
    成功: {"status": "ok", ...} 200；场景不存在 404；流程异常 500。
    """
    import asyncio
    from stash.client import StashClient
    from stash.soft_delete import soft_delete_scene

    data = request.json or {}
    scene_id = str(data.get("scene_id", "")).strip()
    if not scene_id:
        return jsonify({"status": "error", "message": "缺少 scene_id"}), 400

    async def _flow():
        client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)
        return await soft_delete_scene(client, scene_id)

    try:
        result = asyncio.run(_flow())
    except Exception as e:
        logger.exception("软删流程异常 scene=%s", scene_id)
        return jsonify({"status": "error", "message": str(e)[:200]}), 500

    if "error" in result:
        return jsonify({"status": "error", "message": result["error"]}), 404
    return jsonify({"status": "ok", **result}), 200


# ────────────── Bot 线程启动 ──────────────

def _start_bot_thread():
    """在后台线程中启动 Telegram 机器人 polling。"""
    from bot.app import run_bot

    bot_thread = threading.Thread(target=run_bot, kwargs={"mover_handler": mover_handler}, daemon=True, name="tg-bot")
    bot_thread.start()
    logger.info("🤖 Telegram 机器人线程已启动")


if __name__ == "__main__":
    # 初始化校验码采集库（幂等）
    try:
        from db import init_db
        init_db()
        logger.info("💾 校验码采集库就绪 (ENABLE_CHECKSUM=%s)", Config.ENABLE_CHECKSUM)
    except Exception as e:
        logger.warning("校验码库初始化失败: %s", e)

    # 启动 bot 线程（仅当 TG_BOT_TOKEN 已配置时）
    if Config.TG_BOT_TOKEN:
        _start_bot_thread()

    rules = Config.get_mover_rules()
    logger.info("=" * 50)
    logger.info("Stash Webhook Scanner + File Mover 启动")
    logger.info("监听地址: %s:%d", Config.FLASK_HOST, Config.FLASK_PORT)
    if mover_handler.enabled:
        logger.info("搬移规则数: %d", len(rules))
        for i, r in enumerate(rules, 1):
            logger.info("  规则%d [%s]: %s → %s", i, r["name"], r["monitor_path"], r["video_dest_base"])
    else:
        logger.info("搬移模块: 未配置规则，已禁用")
    logger.info("=" * 50)

    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=False,
        use_reloader=False,
    )

