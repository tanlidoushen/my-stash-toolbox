"""
AVDB 聚合磁力源插件 —— 色花堂/x1080x 等多站磁力搜索。

原始 API 返回字段映射为统一 MagnetInfo 结构：
  - download_url → url + hash
  - title        → title（检测"破解"自动加标签）
  - size_mb      → size_mb
  - chinese      → 标签 "中字"
  - hd           → 标签 "高清"
  - site         → 标签（如"色花堂"、"x1080x"）
  - date         → date
  - preview_image → preview_image
"""

from __future__ import annotations

import logging
import re
from typing import ClassVar

import httpx

from config import Config
from bot.magnet_sources.base import BaseMagnetSource, MagnetInfo, MovieInfo

logger = logging.getLogger(__name__)

_BTIH_RE = re.compile(r"btih:([0-9a-fA-F]{40})")


def _clean_title(title: str, number: str | None = None) -> str:
    """清理资源标题：移除 [...]/【...】内容 + 可选番号前缀 + 归一空白。"""
    if not title:
        return title
    cleaned = re.sub(r"\[.*?\]", "", title)
    cleaned = re.sub(r"【.*?】", "", cleaned)
    if number:
        code_clean = re.sub(r"[\s\-_.]", "", number)
        m = re.match(r"^([A-Za-z]+)(\d+)$", code_clean)
        if m:
            prefix, num = m.group(1), m.group(2)
            pattern = prefix + r"[\s\-_.]*" + num + r"[\s\-_.]*"
            cleaned = re.sub(r"^" + pattern, "", cleaned, flags=re.IGNORECASE)
            # 顺带去掉括号内的番号重复段，如 (mida00708)
            cleaned = re.sub(r"\((" + prefix + r"[\s\-_.]*0*" + num + r")\)",
                             "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class AvdbMagnetSource(BaseMagnetSource):
    """AVDB 聚合磁力源（色花堂/x1080x 等多站）。"""

    name: ClassVar[str] = "AVDB"
    priority: ClassVar[int] = 100  # 来源置顶

    @property
    def enabled(self) -> bool:
        return getattr(Config, "AVDB_API_ENABLED", True)

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=Config.AVDB_API_TIMEOUT)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search(self, number: str) -> list[MagnetInfo]:
        """按番号搜索 AVDB 磁力，返回 MagnetInfo 列表。"""
        items = await self._search_torrents(number)
        magnets: list[MagnetInfo] = []
        for item in items:
            m = self._normalize(item)
            if m is not None:
                magnets.append(m)
        logger.info("[AVDB] number=%s 命中 %d 条磁力", number, len(magnets))
        return magnets

    # ══════ 影片元数据接口（轻量版：基于磁力接口提取，无 Emby 依赖） ══════

    async def search_movies(self, number: str, limit: int = 12) -> list[MovieInfo]:
        """按番号搜索影片元数据（轻量版）。

        AVDB 无独立影片库（emby-library 需配置 Emby），从磁力条目提取：
        number / title(清理后) / preview_image(当封面) / 站点标签 / 日期。
        MovieInfo.id 直接用番号（AVDB 以番号聚合）。
        """
        items = await self._search_torrents(number)
        movies = [self._to_movie_info(it) for it in items[:limit]]
        return [m for m in movies if m is not None]

    async def get_movie_detail(self, movie_id: str) -> MovieInfo | None:
        """按番号获取影片"详情"（轻量版）。

        AVDB 无独立详情接口，把 movie_id 当番号再搜一次，取第一条。
        """
        items = await self._search_torrents(movie_id)
        if not items:
            return None
        return self._to_movie_info(items[0])

    async def _search_torrents(self, number: str) -> list[dict]:
        """调 AVDB 磁力接口，返回原始条目列表（失败返回 []）。"""
        await self._ensure_client()
        headers = {"X-API-Key": getattr(Config, "AVDB_API_KEY", "")}
        params = {"keyword": number}
        try:
            resp = await self._client.get(
                Config.AVDB_API_URL,
                params=params,
                headers=headers,
                timeout=Config.AVDB_API_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("[AVDB] 搜索请求失败 number=%s: %s", number, exc)
            return []
        if data.get("code") != 0:
            logger.warning("[AVDB] API 返回 code=%s message=%s",
                           data.get("code"), data.get("message"))
            return []
        return data.get("data") or []

    def _to_movie_info(self, item: dict) -> MovieInfo | None:
        """AVDB 磁力条目 → 轻量 MovieInfo。

        ⚠️ 只映射稳定的影片级字段：number/title/cover/maker/日期。
        **不映射磁力属性标签**（中字/高清/无码/免费/站点）——那些是
        磁力资源属性，不是影片元数据，避免污染详情页标签区。
        影片级标签（演员/题材）AVDB 不提供，保持空。

        - number: 取首个番号（'MIDA-708,MIDA-00708' → 'MIDA-708'）
        - title:  清理 [BT] 等方括号内容 + 去番号前缀
        - maker_name: 从标题 (Moodyz) 括号提取
        """
        number_raw = (item.get("number") or "").strip()
        number = number_raw.split(",")[0].strip() if number_raw else ""
        if not number:
            return None

        raw_title = (item.get("title") or "").strip()
        title = _clean_title(raw_title, number)

        # 片商：标题中 (XXX) 括号内容（如 (Moodyz)），跳过番号重复
        maker = ""
        m = re.search(r"\(([^()]{2,30})\)", raw_title)
        if m:
            cand = m.group(1).strip()
            if cand.upper() != number.split("-")[0]:
                maker = cand

        date = (item.get("post_time") or "").strip()[:10]

        return MovieInfo(
            id=number,
            number=number,
            title=title,
            release_date=date,
            cover_url=(item.get("preview_image") or "").strip(),
            maker_name=maker,
            source=(item.get("site") or "").strip() or "AVDB",
        )

    def _normalize(self, item: dict) -> MagnetInfo | None:
        """原始 AVDB API 条目 → 统一 MagnetInfo。

        映射规则：
          - download_url → url + hash
          - title → title（检测"破解"自动加标签）
          - size_mb → size_mb
          - chinese / hd → tags
          - site → 解析提取站点名（如"色花堂"、"x1080x"）+ 字幕信息
          - date → date
          - preview_image → preview_image

        site 字段格式示例：🌸色花堂🍑中文字幕、🌸x1080x🍑中文字幕
        """
        download_url = (item.get("download_url") or "").strip()
        if not download_url.startswith("magnet:"):
            return None

        m = _BTIH_RE.search(download_url)
        if not m:
            logger.warning("[AVDB] 磁力链接缺少 btih，丢弃: %s", download_url[:80])
            return None

        # ── 构建标签列表 ──
        tags = []

        # 站点名解析：site 字段可能含装饰字符如 🌸🌸🍑，提取纯站点名
        site_raw = (item.get("site") or "").strip()
        site_name = ""
        if site_raw:
            # 常见站点名识别
            for known in ("色花堂", "x1080x"):
                if known in site_raw:
                    site_name = known
                    tags.append(known)
                    break
            # 解析字幕信息（如"🍑中文字幕"）
            if "中字" in site_raw or "中文字幕" in site_raw:
                if "中字" not in tags:
                    tags.append("中字")

        # 中字 / 高清 / 超清 / 无码 / 免费 / UC 布尔字段
        if item.get("chinese") and "中字" not in tags:
            tags.append("中字")
        if item.get("hd"):
            tags.append("高清")
        if item.get("uhd"):
            tags.append("4K")
        if item.get("mosaic") is False:
            tags.append("无码")
        if item.get("free"):
            tags.append("免费")
        if item.get("uc"):
            tags.append("UC")

        # 标题检测"破解"
        title = (item.get("title") or "").strip() or "未命名"
        if "破解" in title:
            if "破解" not in tags:
                tags.append("破解")

        # 日期
        date = (item.get("date") or "").strip()

        # 预览图
        preview = (item.get("preview_image") or "").strip()

        return MagnetInfo(
            hash=m.group(1).upper(),
            title=title,
            url=download_url,
            size_mb=item.get("size_mb") or 0,
            date=date,
            tags=tags,
            source=site_name,
            preview_image=preview,
        )