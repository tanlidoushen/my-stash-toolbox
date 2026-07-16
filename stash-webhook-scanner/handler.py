import os
import logging
import threading
from config import Config

logger = logging.getLogger(__name__)


class FileNotifyHandler:
    def __init__(self):
        self.wait_time = Config.DEBOUNCE_WAIT
        self._target_paths = []
        self._timer = None
        self._lock = threading.Lock()
        self._pipeline_lock = threading.Lock()
        self._allowed_extensions = Config.ALLOWED_EXTENSIONS
        self._allowed_keywords = Config.ALLOWED_KEYWORDS

    def _is_valid_file(self, path):
        """检查路径是否符合允许的后缀和关键词。"""
        if not any(kw in path for kw in self._allowed_keywords):
            logger.debug("路径不包含允许的关键词，已过滤：%s", path)
            return False
        _, ext = os.path.splitext(path)
        if ext.lower() not in self._allowed_extensions:
            logger.debug("文件后缀不匹配，已过滤：%s", path)
            return False
        return True

    def _convert_path(self, path):
        """将虚拟路径前缀替换为实际挂载路径。"""
        for old, new in Config.PATH_PREFIX_MAP:
            if path.startswith(old):
                return new + path[len(old):]
        return path

    def add_change(self, path):
        """注册一个文件变更事件（按后缀和关键词过滤）。"""
        if not self._is_valid_file(path):
            return

        converted = self._convert_path(path)
        with self._lock:
            if converted not in self._target_paths:
                self._target_paths.append(converted)
            self._reset_timer()

    def _reset_timer(self):
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(self.wait_time, self._process_changes)
        self._timer.daemon = True
        self._timer.start()

    def _process_changes(self):
        """防抖到期，取出路径并启动后台扫描流水线。"""
        with self._lock:
            paths = list(set(self._target_paths))
            self._target_paths.clear()

        if not paths:
            return

        logger.info("提交 %d 个文件变更到后台扫描流水线：%s", len(paths), paths)
        t = threading.Thread(target=self._run_scan_pipeline, args=(paths,), daemon=True)
        t.start()

    def _run_scan_pipeline(self, paths):
        """在后台线程中执行扫描流水线，确保同一时间只有一个流水线在跑。"""
        with self._pipeline_lock:
            logger.info("开始扫描流水线（%d 个路径）", len(paths))
            from scanner import run_scans
            run_scans(Config.STASH_URL, paths)
            logger.info("扫描流水线完成（%d 个路径）", len(paths))

        # 流水线执行期间可能又有新通知到达，重新触发防抖
        with self._lock:
            if self._target_paths:
                logger.info("流水线执行期间有新通知到达，重新启动防抖定时器")
                self._reset_timer()
