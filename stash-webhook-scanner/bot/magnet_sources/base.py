"""
Magnet source plugin system — base class and data model.

每个磁力源插件返回统一 MagnetInfo 结构，下游不关心来源。
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import ClassVar

logger = logging.getLogger(__name__)

# 从磁力链接提取 btih 的正则
_BTIH_RE = re.compile(r"btih:([0-9a-fA-F]{40})")


@dataclass
class MagnetInfo:
    """统一磁力条目。

    所有磁力源插件返回此结构，下游展示/离线下载不区分来源。

    字段对齐：
      - hash:      btih 哈希，自动大写归一
      - title:     资源标题
      - url:       磁力链接 magnet:?xt=urn:btih:...
      - size_mb:   大小（MB 数值，方便排序过滤）
      - date:      发布日期 "2026-07-30"
      - tags:      标签列表，如 ["中字", "高清", "破解", "色花堂", "x1080x"]
      - source:    来源站名（展示用，与 tags 不重复）
      - preview_image: 预览图 URL
    """

    # ── 必填字段 ──
    hash: str
    title: str
    size_mb: float

    # ── 可选字段 ──
    url: str = ""          # 磁力链接；留空时由 __post_init__ 从 hash 拼接
    date: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = ""
    preview_image: str = ""

    def __post_init__(self):
        """自动归一化：hash 转大写、url 缺失时从 hash 拼接。"""
        self.hash = self.hash.upper().strip()
        if not self.url:
            self.url = f"magnet:?xt=urn:btih:{self.hash}"

    # ── 便捷工具 ──

    @staticmethod
    def extract_btih(magnet_url: str) -> str | None:
        """从磁力链接提取 btih hash，失败返回 None。"""
        m = _BTIH_RE.search(magnet_url)
        return m.group(1).upper() if m else None

    @staticmethod
    def parse_size(size_str: str) -> float:
        """解析大小字符串 → MB。

        支持 "2.35 GB"、"500 MB"、"1024 MB" 等格式。
        """
        if not size_str:
            return 0.0
        size_str = size_str.strip().upper()
        try:
            if "GB" in size_str:
                return float(size_str.replace("GB", "").strip()) * 1024
            elif "MB" in size_str:
                return float(size_str.replace("MB", "").strip())
            elif "KB" in size_str:
                return float(size_str.replace("KB", "").strip()) / 1024
            else:
                return float(size_str) / (1024 * 1024)  # 视为字节
        except (ValueError, TypeError):
            return 0.0

    def fmt_size(self) -> str:
        """格式化大小展示，如 '2.35 GB'、'500 MB'。"""
        if self.size_mb >= 1024:
            return "%.1f GB" % (self.size_mb / 1024)
        elif self.size_mb > 0:
            return "%d MB" % self.size_mb
        return "未知"


@dataclass
class MovieInfo:
    """统一影片元数据条目（磁力源插件可选提供）。

    供 TG bot 的番号搜索/详情展示使用，下游不区分来源。
    字段对齐 JavDB/AVDB 影片 API 的公共字段。
    """

    id: str                 # 影片在来源站的 ID（详情/磁力回查用）
    number: str             # 番号，如 'MIDA-708'
    title: str = ""
    release_date: str = ""  # '2026-07-30'
    duration: int = 0       # 分钟
    summary: str = ""
    maker_name: str = ""    # 片商
    cover_url: str = ""     # 封面图相对/绝对 URL
    actors: list[dict] = field(default_factory=list)  # [{"name", "gender"}]
    tags: list[dict] = field(default_factory=list)    # [{"name": "..."}]，与 format 模块消费一致
    source: str = ""        # 来源站名（展示用）
    source_name: str = ""   # 来源插件名（如 "JavDB"/"AVDB"，自动选定/详情回查用）

    def to_dict(self) -> dict:
        """转成 dict（兼容旧格式模块的 movie.get(...) 访问）。"""
        return {
            "id": self.id,
            "number": self.number,
            "title": self.title,
            "release_date": self.release_date,
            "duration": self.duration,
            "summary": self.summary,
            "maker_name": self.maker_name,
            "cover_url": self.cover_url,
            "actors": self.actors,
            "tags": self.tags,
            "source": self.source,
        }


class BaseMagnetSource:
    """磁力源插件基类。

    子类只需实现 search() 方法。
    自动发现规则：文件名匹配 *_source.py，排除 base.py。
    """

    # ═══ 元数据（子类覆盖） ═══

    # 来源展示名，如 'JavDB'、'AVDB-色花堂'。留空时用类名。
    name: ClassVar[str] = ""

    # 排序优先级，小在前。默认 100。
    priority: ClassVar[int] = 100

    @property
    def enabled(self) -> bool:
        """是否启用。子类可覆盖，从 Config 或环境变量读取。"""
        return True

    # ═══ 核心接口（子类必须实现） ═══

    async def search(self, number: str) -> list[MagnetInfo]:
        """按番号搜索磁力链接。

        Args:
            number: 归一化后的番号，如 'MIDA-708'、'FPRE-020'

        Returns:
            MagnetInfo 列表。无结果/失败返回 []，不抛异常。
            框架会包裹 try/except，子类不需要额外处理。
        """
        raise NotImplementedError

    # ═══ 可选接口：影片元数据 ═══

    async def search_movies(self, number: str, limit: int = 12) -> list[MovieInfo]:
        """按番号搜索影片元数据（可选实现，默认返回 []）。

        供 TG bot 的番号搜索/详情展示使用。不做精确匹配过滤，
        返回全部匹配结果列表。无结果/失败返回 []。
        """
        return []

    async def get_movie_detail(self, movie_id: str) -> MovieInfo | None:
        """按来源站影片 ID 获取详情（可选实现，默认 None）。"""
        return None

    # ═══ 可选重写 ═══

    def sort_key(self, magnet: MagnetInfo) -> tuple:
        """返回排序键，用于磁力列表展示排序。

        默认策略：优先级 → 中字优先 → 高清优先 → 大小降序。
        子类可覆盖让特定来源的条目优先展示。
        """
        # 从 tags 中检测中字/高清
        cnsub = "中字" in (magnet.tags or [])
        hd = "高清" in (magnet.tags or [])
        return (
            self.priority,
            0 if cnsub else 1,
            0 if hd else 1,
            -(magnet.size_mb or 0),
        )