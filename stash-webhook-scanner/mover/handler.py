import asyncio
import logging
import os
import re
import threading

from config import Config
from cd2_client import get_cd2_client
from .mover import FileMover

logger = logging.getLogger(__name__)


class FileMoveHandler:
    """Webhook 事件处理器：根据通知路径匹配规则，只触发相关的搬移流水线。"""

    def __init__(self):
        self.config = Config
        self.client = get_cd2_client()
        # 为每条规则创建一个 FileMover
        self.rules = []
        for r in Config.get_mover_rules():
            mover = FileMover(self.client, r, Config)
            self.rules.append((r, mover))

        self._debounce_timer = None
        self._lock = threading.Lock()
        self._pipeline_lock = threading.Lock()
        self._pending_indices = set()
        self._monitor_path_id_cache = {}
        self._enabled = bool(self.rules)

        # Telegram bot 引用与事件循环（由 bot 模块在启动后设置）
        self._bot = None
        self._loop = None

    @property
    def enabled(self):
        return self._enabled

    # =================== 通知入口 ===================

    def _is_self_operation(self, item, rule):
        """判断一个通知项是否属于规则 rule 自身的操作。

        重命名操作处理逻辑：
        - 监控目录 → 视频/垃圾目录：自身操作（脚本搬移），忽略
        - 监控目录内部避重名：自身操作（脚本自动加 (N)），忽略
        - 监控目录内部真正重命名：外部操作（用户行为），触发处理
        """
        import re
        
        action = item.get("action", "")
        src = item.get("source_file", "")
        dst = item.get("destination_file", "")
        mp = rule["monitor_path"]
        vb = rule["video_dest_base"]
        td = rule["trash_dest"]

        # 1. 脚本搬移文件到视频目录或垃圾目录
        if action == "rename":
            if src.startswith(mp) and dst.startswith(vb):
                logger.debug("自身操作（搬移到视频目录）: %s → %s", src, dst)
                return True
            if src.startswith(mp) and dst.startswith(td):
                logger.debug("自身操作（搬移到垃圾目录）: %s → %s", src, dst)
                return True

        # 2. 脚本删除文件
        if action == "delete" and src.startswith(mp):
            logger.debug("自身操作（删除文件）: %s", src)
            return True

        # 3. 脚本创建文件到视频/垃圾目录
        if action == "create" and (src.startswith(vb) or src.startswith(td)):
            logger.debug("自身操作（创建文件到视频/垃圾目录）: %s", src)
            return True

        # 4. 监控目录内部的重命名：区分避重名 vs 真正重命名
        if action == "rename" and src.startswith(mp) and dst.startswith(mp):
            src_name = os.path.basename(src)
            dst_name = os.path.basename(dst)
            src_base, src_ext = os.path.splitext(src_name)
            dst_base, dst_ext = os.path.splitext(dst_name)
            
            # 检查是否是为了避重名而添加的 (N) 后缀
            # 模式：原文件名 → 原文件名(N).ext
            if src_ext == dst_ext:
                # 转义正则表达式特殊字符
                escaped_src_base = re.escape(src_base)
                pattern = re.compile(r'^' + escaped_src_base + r'\((\d+)\)$')
                match = pattern.match(dst_base)
                if match:
                    logger.debug("自身操作（避重名重命名，忽略）: %s → %s", src_name, dst_name)
                    return True
            
            # 其他监控目录内部的重命名，视为外部操作，触发处理
            logger.debug("外部操作（监控目录内部重命名，触发）: %s → %s", src_name, dst_name)
            return False

        return False

    def on_file_notify(self, items):
        """收到通知，在识别层过滤自身操作，只将外部通知加入待处理队列。"""
        if not self._enabled:
            return

        matched = set()
        for item in items:
            is_self_op = any(self._is_self_operation(item, rule) for rule, _ in self.rules)
            if is_self_op:
                continue
            src = item.get("source_file", "")
            dst = item.get("destination_file", "")
            for i, (rule, _) in enumerate(self.rules):
                mp = rule["monitor_path"]
                if (src and src.startswith(mp)) or (dst and dst.startswith(mp)):
                    matched.add(i)

        if not matched:
            logger.debug("通知路径不在任何规则的监控范围内，忽略")
            return

        logger.info("通知匹配 %d 条规则: %s", len(matched),
                     [self.rules[i][0]["name"] for i in sorted(matched)])

        with self._lock:
            self._pending_indices.update(matched)
            self._reset_debounce()


    def _get_monitor_path_id(self, path):
        """获取监控目录的 fileId（带缓存）。"""
        if path in self._monitor_path_id_cache:
            return self._monitor_path_id_cache[path]
        try:
            info = self.client.get_file_info(path)
            if info:
                fid = info.get("id", "")
                if fid:
                    self._monitor_path_id_cache[path] = fid
                    logger.debug("监控目录 %s → fileId: %s", path, fid)
                    return fid
        except Exception as e:
            logger.warning("获取监控目录 fileId 失败 %s: %s", path, e)
        self._monitor_path_id_cache[path] = None
        return None

    # =================== 防抖 ===================

    def _reset_debounce(self):
        if self._debounce_timer:
            self._debounce_timer.cancel()
        self._debounce_timer = threading.Timer(
            Config.MOVER_DEBOUNCE_WAIT, self._do_traverse_and_move
        )
        self._debounce_timer.daemon = True
        self._debounce_timer.start()
        logger.debug("防抖定时器已重置（%d 秒），待处理规则: %s",
                     Config.MOVER_DEBOUNCE_WAIT,
                     [self.rules[i][0]["name"] for i in sorted(self._pending_indices)])

    # =================== 流水线执行 ===================

    def _execute_one_rule(self, rule, mover):
        """对单条规则执行：遍历 → 筛选 → 搬移 → 清理。返回结果字典。"""
        name = rule["name"]
        monitor_path = rule["monitor_path"]
        logger.info("─" * 40)
        logger.info("[%s] 开始处理", name)
        logger.info("[%s] 监控目录: %s", name, monitor_path)

        result = {
            "name": name,
            "monitor_path": monitor_path,
        }

        logger.info("[%s] [1/4] 正在递归遍历目录...", name)
        try:
            all_files = self.client.list_directory(monitor_path, force_refresh=True)
        except Exception as e:
            logger.error("[%s] 遍历目录失败: %s", name, e)
            return result | {"error": "遍历目录失败: %s" % e}
        logger.info("[%s]   → 发现 %d 个文件", name, len(all_files))
        if not all_files:
            logger.info("[%s] 目录为空，跳过", name)
            return result | {"files_found": 0, "videos_classified": 0, "trashed": 0, "failed": 0, "cleaned_dirs": 0}

        logger.info("[%s] [2/4] 共发现 %d 个文件，开始分类搬移...", name, len(all_files))
        logger.info("[%s] [3/4] 开始分类搬移...", name)
        try:
            total_video, moved, trashed, failed = mover.process_files(all_files)
        except Exception as e:
            logger.error("[%s] 搬移过程异常: %s", name, e)
            return result | {"error": "搬移异常: %s" % e}
        logger.info("[%s] 搬移统计: 发现 %d | 归类 %d | 待删除 %d | 失败 %d",
                    name, total_video, moved, trashed, failed)

        deleted_dirs = 0
        if rule.get("cleanup_empty_dirs", True):
            logger.info("[%s] [4/4] 开始清理空目录...", name)
            try:
                deleted_dirs = mover.cleanup_empty_dirs(monitor_path)
            except Exception as e:
                logger.warning("[%s] 清理空目录异常: %s", name, e)
            logger.info("[%s]   已删除 %d 个空目录", name, deleted_dirs)

        return result | {
            "files_found": len(all_files),
            "videos_classified": moved,
            "trashed": trashed,
            "failed": failed,
            "cleaned_dirs": deleted_dirs,
        }

    async def _send_classify_result(self, result, chat_id=None):
        """通过 Telegram bot 发送归类结果消息。"""
        target_chat = chat_id or Config.TG_CHAT_ID
        if not target_chat:
            return

        name = result.get("name", "未知")
        monitor_path = result.get("monitor_path", "未知")

        if "error" in result:
            text = (
                "📦 <b>归类失败：[%s]</b>\n"
                "目录: <code>%s</code>\n"
                "错误: %s"
            ) % (name, monitor_path, result["error"])
        else:
            text = (
                "📦 <b>归类完成：[%s]</b>\n"
                "• 监控目录: <code>%s</code>\n"
                "• 发现: %d 个文件\n"
                "• 归类: %d 个视频\n"
                "• 待删除: %d 个\n"
                "• 失败: %d 个\n"
                "• 清理: %d 个空目录"
            ) % (
                name,
                monitor_path,
                result.get("files_found", 0),
                result.get("videos_classified", 0),
                result.get("trashed", 0),
                result.get("failed", 0),
                result.get("cleaned_dirs", 0),
            )

        try:
            sent = await self._bot.send_message(chat_id=target_chat, text=text, parse_mode="HTML")
            if Config.CLASSIFY_DONE_AUTO_DELETE_DELAY > 0:
                from bot.utils import _schedule_auto_delete
                _schedule_auto_delete(
                    self._bot,
                    sent.chat_id,
                    sent.message_id,
                    Config.CLASSIFY_DONE_AUTO_DELETE_DELAY,
                )
        except Exception as e:
            logger.error("发送归类结果消息失败: %s", e)


    # =================== 离线通知处理 ===================

    def on_offline_notify(self, data):
        """处理 CD2 离线任务完成通知：根据 parentId 匹配监控规则，触发搬移流水线。"""
        if not self._enabled:
            return

        offline_file = data.get("body", {}).get("offlineFile", {})
        parent_id = offline_file.get("parentId", "")
        file_name = offline_file.get("name", "未知")

        if not parent_id:
            logger.warning("离线通知缺少 parentId，无法匹配规则")
            return

        # 逐个查询规则的监控目录 ID，与通知中的 parentId 匹配
        matched_indices = []
        for i, (rule, _) in enumerate(self.rules):
            mp = rule["monitor_path"]
            try:
                info = self.client.get_file_info(mp)
                if info and str(info.get("id", "")) == str(parent_id):
                    logger.info("离线通知匹配到规则 [%s]: %s → %s",
                                rule["name"], file_name, mp)
                    matched_indices.append(i)
            except Exception as e:
                logger.debug("查询规则 [%s] 目录信息失败: %s", rule["name"], e)

        if not matched_indices:
            logger.info("离线通知未匹配到任何监控规则: parentId=%s, file=%s", parent_id, file_name)
            return

        # 在后台线程中执行搬移，避免阻塞 webhook 响应
        import threading
        threading.Thread(
            target=self._do_traverse_and_move,
            kwargs={"rule_indices": matched_indices},
            daemon=True,
        ).start()

    def _do_traverse_and_move(self, rule_indices=None, chat_id=None):
        """执行搬移流水线。

        Args:
            rule_indices: 要执行的规则索引列表，None 表示从待处理队列取。
            chat_id: 结果消息发送目标聊天 ID，None 则使用 Config.TG_CHAT_ID。
        """
        if not self._enabled:
            return

        with self._pipeline_lock:
            if rule_indices is None:
                with self._lock:
                    indices = sorted(self._pending_indices)
                    self._pending_indices.clear()
                if not indices:
                    logger.debug("没有待处理的规则，跳过")
                    return
                source = "通知触发"
            else:
                indices = sorted(rule_indices)
                source = "手动触发"

            logger.info("=" * 50)
            logger.info("开始执行搬移流水线（%s，共 %d 条规则）", source, len(indices))
            results = []
            for idx in indices:
                rule, mover = self.rules[idx]
                result = self._execute_one_rule(rule, mover)
                results.append(result)
            logger.info("所有规则处理完毕")
            logger.info("=" * 50)

        # 发送归类结果消息（后台线程 → asyncio 事件循环）
        if self._bot and self._loop and results:
            for result in results:
                asyncio.run_coroutine_threadsafe(
                    self._send_classify_result(result, chat_id),
                    self._loop,
                )

