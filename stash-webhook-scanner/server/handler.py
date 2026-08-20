"""防抖处理器：路径过滤、路径转换、定时触发流水线。"""

import asyncio
import os
import logging
import threading

from config import Config

logger = logging.getLogger(__name__)


class FileNotifyHandler:
    def __init__(self):
        self.wait_time = Config.DEBOUNCE_WAIT
        self._target_paths = {}  # {dest_path: source_path}
        self._timer = None
        self._lock = threading.Lock()
        self._pipeline_lock = threading.Lock()
        self._pipeline_running = False
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

    def add_change(self, path, source_path=None):
        """注册一个文件变更事件（按后缀和关键词过滤）。
        source_path: 文件来源路径（用于目录规则映射判断 JAV/Non-JAV）。
        """
        if not self._is_valid_file(path):
            return
        converted = self._convert_path(path)
        converted_source = self._convert_path(source_path) if source_path else None
        with self._lock:
            if converted not in self._target_paths:
                self._target_paths[converted] = converted_source
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
            if self._pipeline_running:
                # 线程还在跑，不重复启动；新路径已在 _target_paths 中等线程自行取走
                return
            dest_to_source = dict(self._target_paths)
            self._target_paths.clear()
            paths = list(dest_to_source.keys())
            sources = [dest_to_source[p] for p in paths]
        if not paths:
            return
        self._pipeline_running = True
        logger.debug("提交 %d 个文件变更到后台扫描流水线：%s", len(paths), paths)
        t = threading.Thread(
            target=self._run_scan_pipeline, args=(paths, sources), daemon=True
        )
        t.start()

    def _run_scan_pipeline(self, paths, sources):
        """后台线程：动态 drain 路径列表，支持运行中接收新通知。"""
        i = 0
        while i < len(paths):
            # 检查期间有无新通知追加进来
            with self._lock:
                if self._target_paths:
                    new_map = dict(self._target_paths)
                    self._target_paths.clear()
                    for p, s in new_map.items():
                        if p not in paths:
                            paths.append(p)
                            sources.append(s)

            from scrape.pipeline import run_scans

            path = paths[i]
            logger.info("当前共 %d 个路径待处理", len(paths) - i)
            logger.debug("   - 路径 [%d/%d]: %s", i + 1, len(paths), path)
            asyncio.run(run_scans(Config.STASH_URL, [path], source_paths=[sources[i]]))
            i += 1

        self._pipeline_running = False
        # 跑完后如果期间又有新通知，重新触发
        with self._lock:
            if self._target_paths:
                logger.debug("流水线执行期间有新通知到达，重新启动防抖定时器")
                self._reset_timer()