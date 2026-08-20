"""JavDB Search —— 工具函数（图片 URL、封面下载）。
"""

import logging
from urllib.parse import urlparse

import requests as req

from bot.javdb_search_state import _image_prefix_cache

logger = logging.getLogger(__name__)


async def _get_image_prefix(scraper):
    """获取图片 CDN 前缀（带缓存）。"""
    global _image_prefix_cache
    if _image_prefix_cache is None:
        prefix = await scraper.get_web_image_prefix()
        _image_prefix_cache = prefix or ""
        if _image_prefix_cache:
            logger.info("[JavDB Search] 图片 CDN 前缀: %s", _image_prefix_cache)
    return _image_prefix_cache


def _build_cover_url(web_image_prefix, cover_url):
    """从加密 cover_url 提取路径，拼接 web_image_prefix 得到可用的封面 URL。

    cover_url 如 /rhe951l4q/covers/a8/a83YM3.jpg，需去掉首段加密前缀。
    """
    if not cover_url or not web_image_prefix:
        return None
    prefix = web_image_prefix.rstrip("/")
    if cover_url.startswith("http"):
        parsed = urlparse(cover_url)
        path = parsed.path
    else:
        path = cover_url if cover_url.startswith("/") else "/%s" % cover_url
    # 去掉第一个路径段（加密前缀），只保留 /covers/... 部分
    parts = path.lstrip("/").split("/", 1)
    if len(parts) == 2:
        path = "/" + parts[1]
    return "%s%s" % (prefix, path)


_COVER_USER_AGENTS = (
    "Dart/3.5 (dart:io)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
)


def _download_cover(url):
    """下载封面图片 bytes（绕过 CDN 反盗链；失败时换浏览器 UA 重试）。"""
    for ua in _COVER_USER_AGENTS:
        try:
            resp = req.get(url, headers={"User-Agent": ua}, timeout=15)
            resp.raise_for_status()
            if resp.content:
                return resp.content
        except Exception as e:
            logger.warning("[JavDB Search] 下载封面失败 (%s): %s", ua[:24], e)
    return None


async def safe_edit_or_reply(update, status_msg, caption, reply_markup):
    """安全编辑消息：若 status_msg 仍在就用 edit_text，否则用 reply_text。"""
    from telegram.error import BadRequest

    try:
        await status_msg.edit_text(
            caption, reply_markup=reply_markup, parse_mode="HTML"
        )
    except BadRequest:
        await update.message.reply_text(
            caption, reply_markup=reply_markup, parse_mode="HTML"
        )
