import os
import logging
import sys
import hashlib
import time
from flask import Flask, request, jsonify
from handler import FileNotifyHandler
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

app = Flask(__name__)

# Mute Werkzeug access logs
logging.getLogger("werkzeug").setLevel(logging.ERROR)

handler = FileNotifyHandler()


# 请求去重：最近 5 秒内收到过的请求指纹
_RECENT_DEDUP_SECONDS = 5
_recent_request_hashes = {}  # hash -> timestamp


def _is_duplicate_request(body_bytes):
    """检查是否为重复请求（相同 body 在 _RECENT_DEDUP_SECONDS 内到达过）。"""
    now = time.time()
    req_hash = hashlib.md5(body_bytes).hexdigest()

    # 清理过期记录
    expired = [h for h, ts in _recent_request_hashes.items() if now - ts > _RECENT_DEDUP_SECONDS]
    for h in expired:
        del _recent_request_hashes[h]

    if req_hash in _recent_request_hashes:
        return True
    _recent_request_hashes[req_hash] = now
    return False


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
    if _is_duplicate_request(raw_body):
        logger = logging.getLogger(__name__)
        logger.info("收到重复通知，已忽略（%.3fs 内相同请求）", _RECENT_DEDUP_SECONDS)
        return jsonify({"状态": "成功", "消息": "重复通知已忽略"}), 200

    notifications = []
    for item in data.get("data", []):
        src = item.get("source_file", "未知路径")
        dst = item.get("destination_file", "无")
        action_cn = _translate_action(item.get("action", "未知"), src, dst)
        is_dir_cn = "目录" if item.get("is_dir") == "true" else "文件"
        notifications.append({
            "动作": action_cn,
            "类型": is_dir_cn,
            "源路径": src,
            "目标路径": dst,
        })
        if action_cn in ("移动", "重命名") and dst != "无":
            handler.add_change(dst)
        elif action_cn == "创建":
            handler.add_change(src)

    if notifications:
        logging.getLogger(__name__).info(
            "收到 %d 条通知：%s", len(notifications), notifications
        )
    return jsonify({"状态": "成功", "消息": "已接收文件系统通知"}), 200


if __name__ == "__main__":
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=False,
        use_reloader=False,
    )
