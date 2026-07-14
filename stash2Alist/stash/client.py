"""Stash GraphQL 客户端 - 查询场景文件路径"""
import logging
from typing import Optional

import httpx

from ..cache import TTLCache

logger = logging.getLogger("stash2alist.stash")


class StashClient:
    """通过 Stash GraphQL API 查询场景信息"""

    def __init__(self, stash_url: str, api_key: str = "", cache_ttl: int = 3600, cache_maxsize: int = 1000):
        # 确保 URL 指向 GraphQL 端点
        self.graphql_url = stash_url.rstrip("/")
        if not self.graphql_url.endswith("/graphql"):
            self.graphql_url += "/graphql"

        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["ApiKey"] = api_key

        self.cache = TTLCache(maxsize=cache_maxsize)
        self.cache_ttl = cache_ttl  # 固定 TTL，缓存场景文件路径
        self._client = httpx.AsyncClient(timeout=10.0)

    async def get_file_path(self, scene_id: int) -> Optional[str]:
        """通过场景 ID 查询第一个文件的完整路径，带缓存"""
        cache_key = f"scene_path:{scene_id}"

        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached

        query = {
            "query": f"""
            query {{
              findScene(id: {scene_id}) {{
                id
                files {{ path }}
              }}
            }}
            """
        }

        try:
            resp = await self._client.post(self.graphql_url, headers=self.headers, json=query)
            resp.raise_for_status()
            data = resp.json()
        except httpx.RequestError as e:
            logger.error(f"查询 Stash 失败 scene_id={scene_id}: {e}")
            return None
        except ValueError as e:
            logger.error(f"Stash 返回非 JSON scene_id={scene_id}: {e}")
            return None

        scene = data.get("data", {}).get("findScene")
        if not scene or str(scene.get("id")) != str(scene_id):
            logger.warning(f"场景未找到 scene_id={scene_id}")
            return None

        files = scene.get("files", [])
        if not files:
            logger.warning(f"场景无文件 scene_id={scene_id}")
            return None

        path = files[0].get("path", "")
        if not path:
            logger.warning(f"场景文件路径为空 scene_id={scene_id}")
            return None

        # 确保路径以 / 开头
        if not path.startswith("/"):
            path = "/" + path

        await self.cache.set(cache_key, path, self.cache_ttl)
        logger.info(f"查询到文件路径 scene_id={scene_id}: {path}")
        return path
