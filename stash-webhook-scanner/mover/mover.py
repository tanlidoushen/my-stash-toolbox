import logging
import os
import re
from collections import defaultdict

logger = logging.getLogger(__name__)


class FileMover:
    """单条规则的搬移逻辑（分类、分卷、清理）。"""

    def __init__(self, cd2_client, rule, global_config):
        self.client = cd2_client
        self.rule = rule
        self.g = global_config

    # =================== 分类 ===================

    def classify(self, file_info):
        if file_info.get("isDirectory"):
            logger.debug("跳过目录: %s", file_info.get("name", ""))
            return None

        name = file_info.get("name", "")
        ext = os.path.splitext(name)[1].lower()
        if ext not in self.g.VIDEO_EXTENSIONS:
            logger.debug("非视频后缀（待删除）: %s", name)
            return "trash"

        name_lower = name.lower()
        for kw in self.rule["trash_keywords"]:
            if kw in name_lower:
                logger.debug("关键词匹配（待删除）: %s → 匹配 '%s'", name, kw)
                return "trash"

        raw_size = file_info.get("size", 0)
        try:
            fsize = int(raw_size) if raw_size is not None else 0
        except (ValueError, TypeError):
            fsize = 0
        if fsize < self.rule["small_file_size"]:
            logger.debug("小于尺寸阈值（待删除）: %s (%d bytes)", name, fsize)
            return "trash"

        return "video"

    # =================== 归类后：自动分卷 ===================

    def _resolve_video_folder(self):
        base = self.rule["video_dest_base"]
        prefix = self.rule["folder_prefix"]
        max_files = self.rule["max_files_per_folder"]

        try:
            entries = self.client.get_sub_files(base, force_refresh=False)
        except Exception as e:
            logger.warning("[%s] 无法列出目标目录 %s: %s", self.rule["name"], base, e)
            return base

        folders = []
        for e in entries:
            if not e.get("isDirectory"):
                continue
            ename = e.get("name", "")
            folders.append(ename)

        pattern = re.compile(r"^" + re.escape(prefix) + r"(\d+)$")
        existing = []
        for f in folders:
            m = pattern.match(f)
            if m:
                existing.append((int(m.group(1)), f))
        existing.sort(key=lambda x: x[0])

        for _num, name in existing:
            folder = f"{base}/{name}"
            try:
                subfiles = self.client.get_sub_files(folder, force_refresh=False)
                file_count = sum(1 for sf in subfiles if not sf.get("isDirectory"))
                remaining = max_files - file_count
                logger.debug("[%s] 目录 %s: %d/%d（剩余 %d）", self.rule["name"], name, file_count, max_files, remaining)
                if remaining > 0:
                    return folder
            except Exception as e:
                logger.warning("[%s] 统计文件数失败 %s: %s", self.rule["name"], name, e)
                return folder

        latest_num = existing[-1][0] if existing else 0
        new_num = latest_num + 1
        new_name = f"{prefix}{new_num:03d}"
        new_folder = f"{base}/{new_name}"
        logger.info("[%s] 新建分卷目录: %s", self.rule["name"], new_folder)
        if self.client.ensure_dir(new_folder):
            return new_folder
        else:
            logger.error("[%s] 无法创建分卷目录 %s，回退到 %s", self.rule["name"], new_folder, base)
            return base

    # =================== 待删除：按后缀分目录 ===================

    def _resolve_trash_folder(self, ext):
        sub = ext.lstrip(".")
        folder = f"{self.rule['trash_dest']}/{sub}"
        self.client.ensure_dir(folder)
        return folder

    # =================== 批量搬移 ===================

    def move_batch(self, file_paths, dest_dir):
        if not file_paths:
            return 0, 0

        logger.info("[%s] 批量搬移 %d 个文件 → %s", self.rule["name"], len(file_paths), dest_dir)
        success = 0
        fail = 0

        if not self.client.ensure_dir(dest_dir):
            logger.error("[%s] 目标目录不可用: %s", self.rule["name"], dest_dir)
            return 0, len(file_paths)

        try:
            self.client.move_file(file_paths, dest_dir, self.g.CONFLICT_POLICY)
            success = len(file_paths)
            logger.info("[%s] 批量搬移成功: %d 个", self.rule["name"], success)
        except Exception as e:
            logger.warning("[%s] 批量搬移失败，降级为逐文件: %s", self.rule["name"], e)
            for fp in file_paths:
                try:
                    self.client.move_file(fp, dest_dir, self.g.CONFLICT_POLICY)
                    success += 1
                except Exception as e2:
                    logger.error("[%s] 搬移失败: %s → %s: %s", self.rule["name"], fp, dest_dir, e2)
                    fail += 1

        return success, fail

    # =================== 流水线 ===================

    def process_files(self, files):
        trash_by_ext = defaultdict(list)
        video_paths = []
        total_video = 0

        for f in files:
            category = self.classify(f)
            if category is None:
                continue
            fpath = f.get("fullPathName", "")
            if not fpath:
                continue
            total_video += 1
            if category == "trash":
                ext = os.path.splitext(f.get("name", ""))[1].lower()
                trash_by_ext[ext].append(fpath)
            else:
                video_paths.append(fpath)

        video_moved = video_failed = 0
        if video_paths:
            logger.info("[%s] 归类视频 %d 个，按父目录分组分卷搬移", self.rule["name"], len(video_paths))
            by_parent = defaultdict(list)
            for fp in video_paths:
                by_parent[os.path.dirname(fp)].append(fp)
            for parent, paths in sorted(by_parent.items()):
                logger.debug("[%s] 父目录 %s: %d 个视频", self.rule["name"], parent, len(paths))
                batch = []
                for fp in paths:
                    batch.append(fp)
                    if len(batch) >= self.rule["max_files_per_folder"]:
                        folder = self._resolve_video_folder()
                        s, f = self.move_batch(batch, folder)
                        video_moved += s
                        video_failed += f
                        batch = []
                if batch:
                    folder = self._resolve_video_folder()
                    s, f = self.move_batch(batch, folder)
                    video_moved += s
                    video_failed += f

        trash_moved = trash_failed = 0
        if trash_by_ext:
            logger.info("[%s] 待删除 %d 个，按后缀+父目录分组搬移", self.rule["name"],
                        sum(len(v) for v in trash_by_ext.values()))
            for ext, paths in sorted(trash_by_ext.items()):
                folder = self._resolve_trash_folder(ext)
                by_parent = defaultdict(list)
                for fp in paths:
                    by_parent[os.path.dirname(fp)].append(fp)
                for parent, parent_paths in sorted(by_parent.items()):
                    logger.debug("[%s] 父目录 %s: %d 个待删除(%s)", self.rule["name"], parent, len(parent_paths), ext)
                    s, f = self.move_batch(parent_paths, folder)
                    trash_moved += s
                    trash_failed += f

        return total_video, video_moved, trash_moved, video_failed + trash_failed

    # =================== 空目录清理 ===================

    def scan_all_dirs_and_files(self, root_path):
        all_files = []
        all_dirs = []
        queue = [root_path]
        visited = set()
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            try:
                entries = self.client.get_sub_files(current, force_refresh=False)
            except Exception as e:
                logger.warning("[%s] 遍历失败（跳过）: %s — %s", self.rule["name"], current, e)
                continue
            all_dirs.append(current)
            for entry in entries:
                if entry.get("isDirectory"):
                    sub_path = entry.get("fullPathName") or entry.get("name", "")
                    if sub_path and sub_path not in visited:
                        queue.append(sub_path)
                else:
                    all_files.append(entry)
        return all_files, all_dirs

    def cleanup_empty_dirs(self, source_path):
        logger.info("[%s] 开始清理空目录: %s", self.rule["name"], source_path)
        _, all_dirs = self.scan_all_dirs_and_files(source_path)
        all_dirs.sort(key=lambda x: x.count("/"), reverse=True)
        deleted_count = 0
        for dir_path in all_dirs:
            if dir_path == source_path:
                continue
            try:
                entries = self.client.get_sub_files(dir_path, force_refresh=False)
                if not entries:
                    logger.debug("[%s] 删除空目录: %s", self.rule["name"], dir_path)
                    self.client.delete_file(dir_path)
                    deleted_count += 1
            except Exception as e:
                logger.debug("[%s] 检查/删除目录失败 %s: %s", self.rule["name"], dir_path, e)
        logger.info("[%s] 空目录清理完成，共删除 %d 个", self.rule["name"], deleted_count)
        return deleted_count

