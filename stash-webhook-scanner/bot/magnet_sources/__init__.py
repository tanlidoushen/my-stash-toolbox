"""
磁力源插件系统 — 管理器（自动发现 + 编排 + 合并去重）。

用法：
    manager = get_magnet_manager()
    magnets = await manager.search_all("MIDA-708")
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import sys

from bot.magnet_sources.base import BaseMagnetSource, MagnetInfo, MovieInfo

logger = logging.getLogger(__name__)

# 默认自动发现目录（相对本文件）
_SOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))


class MagnetSourceManager:
    """磁力源管理器：自动发现、编排搜索、合并去重。"""

    def __init__(self):
        self._sources: list[BaseMagnetSource] = []
        self._loaded = False

    # ═══════ 发现 / 注册 ═══════

    def discover(self, source_dir: str | None = None):
        """自动发现 magnet_sources/ 下所有 BaseMagnetSource 子类。

        匹配规则：文件名 *_source.py（排除 base.py / __init__.py）。
        结果缓存，只扫描一次。
        """
        if self._loaded:
            return
        self._loaded = True

        src_dir = os.path.abspath(source_dir) if source_dir else _SOURCE_DIR
        if not os.path.isdir(src_dir):
            logger.debug("磁力源目录不存在: %s", src_dir)
            return

        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

        for fname in sorted(os.listdir(src_dir)):
            if not fname.endswith("_source.py"):
                continue
            if fname in ("base.py", "__init__.py"):
                continue
            module_name = fname[:-3]
            try:
                module = __import__(f"bot.magnet_sources.{module_name}",
                                    fromlist=[module_name])
            except Exception as e:
                # 尝试相对导入降级
                try:
                    module = __import__(module_name)
                except Exception as e2:
                    logger.error("加载磁力源插件 %s 失败: %s / %s", fname, e, e2)
                    continue
            for _name, obj in inspect.getmembers(module, inspect.isclass):
                if obj is BaseMagnetSource:
                    continue
                if issubclass(obj, BaseMagnetSource):
                    source = obj()
                    self._sources.append(source)
                    logger.info("已加载磁力源: %s (priority=%d, enabled=%s)",
                                source.name, source.priority, source.enabled)

    def register(self, source: BaseMagnetSource):
        """手动注册一个磁力源（用于测试或内建源）。"""
        self._sources.append(source)
        self._loaded = True

    # ═══════ 编排 ═══════

    async def search_all(self, number: str) -> list[MagnetInfo]:
        """并行搜索所有已启用的磁力源，合并去重后返回。

        流程：
          1. 过滤 enabled=True 的源
          2. asyncio.gather 并行搜索（每个源独立 try/except）
          3. 按 btih hash 去重（来源优先级高的优先保留）
          4. 按 sort_key 排序
        """
        self.discover()
        sources = [s for s in self._sources if s.enabled]
        if not sources:
            logger.info("无启用的磁力源")
            return []

        sources_sorted = sorted(sources, key=lambda s: s.priority)

        async def _run(src: BaseMagnetSource) -> list[MagnetInfo]:
            try:
                magnets = await src.search(number)
                return magnets or []
            except Exception as e:
                logger.warning("磁力源 %s 搜索失败 number=%s: %s",
                               src.name, number, e)
                return []

        results = await asyncio.gather(*(_run(s) for s in sources_sorted))

        # ── 合并去重（按 btih hash，来源优先级高的优先保留） ──
        seen: set[str] = set()
        merged: list[MagnetInfo] = []
        for src, magnets in zip(sources_sorted, results):
            for m in magnets:
                h = (m.hash or "").lower()
                if h:
                    if h in seen:
                        continue
                    seen.add(h)
                merged.append(m)

        # ── 按 sort_key 排序 ──
        #  每个磁力用所属源排序；source 优先级高的整体靠前
        #  简化：用 (来源priority, 中字, 高清, -size)
        sort_source_lookup = {}
        for src, magnets in zip(sources_sorted, results):
            for m in magnets:
                sort_source_lookup[id(m)] = src

        def _sort_key(m: MagnetInfo):
            src = sort_source_lookup.get(id(m))
            if src is not None:
                return src.sort_key(m)
            # 兜底
            return (100, 0 if "中字" in m.tags else 1,
                    0 if "高清" in m.tags else 1, -(m.size_mb or 0))

        merged.sort(key=_sort_key)
        return merged

    @property
    def sources(self) -> list[BaseMagnetSource]:
        """返回已发现的磁力源列表。"""
        self.discover()
        return list(self._sources)

    # ═══════ 影片元数据编排（TG bot 搜索/详情展示用） ═══════

    async def search_movies(self, number: str, limit: int = 12) -> list[MovieInfo]:
        """按番号搜索影片元数据，聚合所有已启用源的结果。

        顺序按 priority 排列（高优先级源靠前），不去重
        （不同源可能返回不同影片，由下游按 number 区分）。
        每个 MovieInfo 打上 source_name（来源插件名），供自动选定/详情回查。
        """
        self.discover()
        sources = [s for s in self._sources if s.enabled]
        results: list[MovieInfo] = []
        for src in sorted(sources, key=lambda s: s.priority):
            try:
                movies = await src.search_movies(number, limit=limit)
                if movies:
                    for m in movies:
                        m.source_name = getattr(src, "name", "") or ""
                    results.extend(movies)
            except Exception as e:
                logger.warning("影片搜索源 %s 失败 number=%s: %s",
                               getattr(src, "name", type(src).__name__), number, e)
        return results

    async def get_movie_detail(self, movie_id: str, source: str | None = None) -> MovieInfo | None:
        """按来源站影片 ID 获取详情。

        Args:
            movie_id: 来源站影片 ID（如 JavDB 视频 id / AVDB 番号）
            source: 指定来源插件名（如 "JavDB"）时只从该源取详情；
                    省略时按优先级依次尝试各源（原行为）。

        自动选定路径必须传 source——否则 AVDB 会把 JavDB 的 id 当番号误搜。
        """
        self.discover()
        for src in sorted(self._sources, key=lambda s: s.priority):
            if not src.enabled:
                continue
            if source and (getattr(src, "name", "") or "") != source:
                continue
            try:
                movie = await src.get_movie_detail(movie_id)
                if movie:
                    return movie
            except Exception as e:
                logger.warning("影片详情源 %s 失败 movie_id=%s: %s",
                               getattr(src, "name", type(src).__name__), movie_id, e)
        return None

    # ═══════ 自动选定 ═══════

    @staticmethod
    def _normalize_code(code: str) -> str:
        """番号归一化：大写 + 去空格/连字符/下划线/点（'ADN-188' == 'adn188'）。"""
        import re
        return re.sub(r"[\s\-_.]", "", (code or "")).upper()

    def pick_movie_auto(self, movies: list[MovieInfo], query_code: str) -> MovieInfo | None:
        """自动选定影片（跳过候选列表）。

        规则：
          1. 精确匹配：归一化番号 == 查询番号（排除 ADN-088 / AD-1188 这类模糊命中）
          2. 优先源：按 MAGNET_AUTO_PICK_PREFER 配置的源顺序，取该源第一条精确匹配
          3. 无优先源命中 → 回退其他源第一条精确匹配
          4. 无任何精确匹配（内部无法判断）→ 返回 None，调用方展示候选列表
        """
        from config import Config
        prefer = [s.strip() for s in
                  getattr(Config, "MAGNET_AUTO_PICK_PREFER", "JavDB").split(",") if s.strip()]
        q = self._normalize_code(query_code)
        exact = [m for m in movies if self._normalize_code(m.number) == q]
        if not exact:
            return None
        for src in prefer:
            for m in exact:
                if (m.source_name or "").strip().lower() == src.lower():
                    return m
        return exact[0]


# ── 全局单例 ──

_manager: MagnetSourceManager | None = None


def get_magnet_manager() -> MagnetSourceManager:
    """返回全局磁力源管理器单例。"""
    global _manager
    if _manager is None:
        _manager = MagnetSourceManager()
    return _manager


__all__ = [
    "MagnetInfo",
    "MovieInfo",
    "BaseMagnetSource",
    "MagnetSourceManager",
    "get_magnet_manager",
]
