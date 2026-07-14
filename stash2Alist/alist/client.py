"""Alist 客户端 - 拼接 /d/{path} 并跟随 302 获取文件最终直链（透传客户端 UA）"""
import asyncio
import hashlib
import logging
import time
from typing import Optional
from urllib.parse import quote, urlparse, parse_qs

import httpx

from ..cache import TTLCache

logger = logging.getLogger("stash2alist.alist")


class AlistClient:
    """通过拼接 /d/{path} 并跟随 302 重定向获取文件最终下载直链"""

    def __init__(
        self,
        alist_url: str,
        token: str = "",
        cache_maxsize: int = 1000,
        timeout: int = 1,
        retries: int = 3,
        retry_delay: float = 0.5,
    ):
        self.base_url = alist_url.rstrip("/")
        # 保留 token 参数仅为向后兼容，新方式不再使用 API
        self.cache = TTLCache(maxsize=cache_maxsize)
        self.request_timeout = timeout
        self.request_retries = retries
        self.request_retry_delay = retry_delay
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout), follow_redirects=False)

    @staticmethod
    def _calc_dynamic_ttl(url: str, safety_margin: int = 300) -> int:
        """从直链 URL 解析 t 参数（Unix 时间戳），计算动态 TTL。

        返回: max(1, t - now - safety_margin)；
              如无法解析则返回 0（不缓存）。
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            t_str = params.get("t")
            if t_str and t_str[0].isdigit():
                expire_ts = int(t_str[0])
                now_ts = int(time.time())
                return max(1, expire_ts - now_ts - safety_margin)
        except Exception:
            pass
        return 0

    async def verify_path(self, alist_path: str) -> bool:
        """验证 Alist 路径是否存在（通过 HEAD /d/{path} 快速检测）"""
        try:
            encoded_path = quote(alist_path, safe="/")
            check_url = f"{self.base_url}/d{encoded_path}"
            resp = await self._client.head(check_url, timeout=httpx.Timeout(15.0))
            # 200/302 都表示路径有效
            return resp.status_code in (200, 302)
        except Exception:
            return False

    async def get_direct_link(self, alist_path: str, client_ua: str = "") -> Optional[str]:
        """拼接 /d/{path} 并跟随 302 获取最终直链（透传客户端 UA）"""
        ua_suffix = hashlib.md5(client_ua.encode()).hexdigest()[:8] if client_ua else "default"
        cache_key = f"alink:{alist_path}@{ua_suffix}"

        cached = await self.cache.get(cache_key)
        if cached is not None:
            logger.info(f"缓存命中: {cached}")
            return cached

        # 拼接 Alist 直接下载地址（保留正斜杠，编码特殊字符）
        encoded_path = quote(alist_path, safe="/")
        direct_url = f"{self.base_url}/d{encoded_path}"

        headers = {}
        if client_ua:
            headers["User-Agent"] = client_ua

        filename = alist_path.rsplit("/", 1)[-1] if "/" in alist_path else alist_path
        last_error = None

        for attempt in range(1, self.request_retries + 1):
            try:
                # 不跟随重定向，手工处理 302
                resp = await self._client.get(
                    direct_url,
                    headers=headers,
                )
            except httpx.TimeoutException:
                last_error = f"/d/ 请求超时 (attempt {attempt}/{self.request_retries}) {filename}"
                logger.warning(last_error)
                if attempt < self.request_retries:
                    await asyncio.sleep(self.request_retry_delay)
                continue
            except httpx.RequestError as e:
                last_error = f"/d/ 请求失败 {filename}: {e}"
                logger.error(last_error)
                return None
            # 请求成功，跳出重试循环
            break
        else:
            logger.error(last_error)
            return None

        if resp.status_code == 302:
            location = resp.headers.get("Location")
            if location:
                ttl = self._calc_dynamic_ttl(location)
                if ttl > 0:
                    expire_time = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(time.time() + ttl + 300)
                    )
                    logger.info(
                        f"获取直链并缓存(302): {location}  "
                        f"TTL: {ttl}s（直链过期: {expire_time}，预留 300s）"
                    )
                    await self.cache.set(cache_key, location, ttl)
                else:
                    logger.info(
                        f"获取直链(302): {location}  "
                        f"URL 无 t 参数，不缓存"
                    )
                return location
            else:
                logger.warning(f"/d/ 返回 302 但无 Location header {filename}")
                return None
        elif resp.status_code == 200:
            # Alist 直接返回内容（本地文件等），返回原始 /d/ URL
            ttl = self._calc_dynamic_ttl(direct_url)
            if ttl > 0:
                expire_time = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(time.time() + ttl + 300)
                )
                logger.info(
                    f"获取直链并缓存(200 直接): {direct_url}  "
                    f"TTL: {ttl}s（直链过期: {expire_time}，预留 300s）"
                )
                await self.cache.set(cache_key, direct_url, ttl)
            else:
                logger.info(
                    f"获取直链(200 直接): {direct_url}  "
                    f"URL 无 t 参数，不缓存"
                )
            return direct_url
        else:
            logger.warning(f"/d/ 返回 {resp.status_code} {filename}: {resp.text[:100]}")
            return None
