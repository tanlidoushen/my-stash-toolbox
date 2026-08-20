"""AVDB 番号搜索插件 — 通过 AVDB API 获取中文标题。

从 AVDB（色花堂）API 搜索番号，筛选 🌸色花堂🍑中文字幕 板块的资源，
提取中文标题并清理 [...] 标记和番号前缀后作为标题补充。
"""

import logging
import os
import re

import httpx

from plugins.base import BasePlugin

logger = logging.getLogger("extsrc")


# ──────── AVDB API constants（通过环境变量注入，勿硬编码真实 Key） ────────

AVDB_API_URL = os.environ.get("AVDB_API_URL", "http://<avdb-server>:18000/api/v1/articles/torrents")
AVDB_API_KEY = os.environ.get("AVDB_API_KEY", "<your-avdb-api-key>")
TARGET_SITE = "🌸色花堂🍑中文字幕"


# ──────── Internal helpers ────────

def _clean_title(title, japanese_code=None):
    """Remove [...] brackets content and optional japanese_code prefix from title."""
    if not title:
        return title
    # Remove [...] and 【...】 brackets and their contents
    cleaned = re.sub(r'\[.*?\]', '', title)
    cleaned = re.sub(r'【.*?】', '', cleaned)
    # Remove leading japanese_code if present (e.g. "JUR-769 " at start)
    if japanese_code:
        code_clean = re.sub(r'[\s\-_.]', '', japanese_code)
        m = re.match(r'^([A-Za-z]+)(\d+)$', code_clean)
        if m:
            prefix, number = m.group(1), m.group(2)
            pattern = prefix + r'[\s\-_.]*' + number + r'[\s\-_.]*'
            cleaned = re.sub(r'^' + pattern, '', cleaned, flags=re.IGNORECASE)
    # Normalise whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


# ──────── Scraper class ────────

class AVDBScraper:
    """Minimal AVDB API scraper — no Stash integration."""

    def __init__(self):
        self._client = None

    async def _ensure_client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=15.0)

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search_by_code(self, code):
        """Search AVDB by code. Returns list of result dicts or None."""
        await self._ensure_client()

        headers = {"X-API-Key": AVDB_API_KEY}
        params = {"keyword": code}

        try:
            resp = await self._client.get(
                AVDB_API_URL, params=params, headers=headers, timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("         - [Plugin:avdb] API 请求失败: %s", exc)
            return None

        if data.get("code") != 0:
            logger.warning("         - [Plugin:avdb] API 返回失败: %s", data.get("message"))
            return None

        items = data.get("data") or []
        if not items:
            logger.info("         - [Plugin:avdb] 无搜索结果")
            return None

        return items

    @staticmethod
    def filter_chinese_subtitle(items):
        """Filter items to only those from the target site."""
        for item in items:
            site = (item.get("site") or "").strip()
            if site == TARGET_SITE:
                return item
        logger.info("         - [Plugin:avdb] 未找到 %s 板块的结果", TARGET_SITE)
        return None


# ──────── Plugin class ────────

class AvdbPlugin(BasePlugin):
    """Plugin that scrapes AVDB for Chinese title."""

    @property
    def name(self):
        return "avdb"

    async def scrape(self, japanese_code, scene_info=None):
        if not japanese_code:
            return {}

        logger.info("         - [Plugin:avdb] 搜索番号 %s", japanese_code)

        scraper = AVDBScraper()
        try:
            items = await scraper.search_by_code(japanese_code)
            if not items:
                return {}

            target = scraper.filter_chinese_subtitle(items)
            if not target:
                return {}

            raw_title = (target.get("title") or "").strip()
            if not raw_title:
                logger.info("         - [Plugin:avdb] 目标资源无标题")
                return {}

            # ── 清理标题（移除 [...] 和番号前缀）──
            cleaned = _clean_title(raw_title, japanese_code)
            if not cleaned:
                cleaned = raw_title

            logger.info("         - [Plugin:avdb] 获取中文标题: %s", cleaned[:80])
            return {"title": cleaned}

        except Exception as exc:
            logger.error("         - [Plugin:avdb] 错误: %s", exc)
            return {}
        finally:
            await scraper.close()
