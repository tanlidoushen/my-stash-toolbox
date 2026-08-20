"""标记同步 HTTP 客户端：httpx 异步版 TTClient + TPDBClient。

从 stash-marker-sync 移植，urllib → httpx 异步化。
"""
import logging

import httpx

logger = logging.getLogger(__name__)

TT_BASE = "https://timestamp.trade"
TPDB_API_BASE = "https://api.theporndb.net"


class TTClient:
    """timestamp.trade HTTP 客户端（httpx 异步版）。"""

    def __init__(self, proxy: str = None):
        self._client = None
        self._proxy = proxy

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            kwargs = {
                "timeout": httpx.Timeout(30.0),
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    "Accept": "application/json,text/plain,*/*",
                },
            }
            if self._proxy:
                kwargs["proxy"] = self._proxy
            self._client = httpx.AsyncClient(**kwargs)
        return self._client

    async def get_markers(self, stash_id: str) -> dict | None:
        """stash_id → tt 场景映射（scene_id）。返回 dict 或 None。"""
        try:
            c = await self._get_client()
            r = await c.get(f"{TT_BASE}/get-markers/{stash_id}")
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.warning("TT get-markers 失败: %s", e)
        return None

    async def get_scene(self, scene_id: str) -> dict | None:
        """json-scene/{scene_id} 全量元数据。返回 dict 或 None。"""
        try:
            c = await self._get_client()
            r = await c.get(f"{TT_BASE}/json-scene/{scene_id}")
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.warning("TT json-scene 失败: %s", e)
        return None

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


class TPDBClient:
    """ThePornDB REST 客户端（httpx 异步版，Bearer 认证）。"""

    def __init__(self, api_key: str, proxy: str = None):
        self._api_key = api_key
        self._client = None
        self._proxy = proxy

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            kwargs = {
                "timeout": httpx.Timeout(30.0),
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                },
            }
            if self._proxy:
                kwargs["proxy"] = self._proxy
            self._client = httpx.AsyncClient(**kwargs)
        return self._client

    async def get_scene(self, tpdb_id: str) -> dict | None:
        """按 theporndb stash_id 查场景，返回 data 部分（含 markers/movies）。"""
        try:
            c = await self._get_client()
            r = await c.get(f"{TPDB_API_BASE}/scenes/{tpdb_id}")
            if r.status_code == 200:
                d = r.json()
                return d.get("data") or {}
        except Exception as e:
            logger.warning("TPDB get_scene 失败: %s", e)
        return None

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None