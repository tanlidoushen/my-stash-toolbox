"""Stash GraphQL 客户端 —— 异步 httpx 实现，带传输层失败重试。"""

import asyncio
import logging

import httpx

from config import Config

logger = logging.getLogger(__name__)


class StashClient:
    """封装 Stash GraphQL API 的异步请求逻辑。"""

    def __init__(self, stash_url, api_key=None, timeout=120,
                 retry_count=None, retry_delay=None):
        self.stash_url = stash_url
        self.api_key = api_key
        self.timeout = timeout
        self.retry_count = retry_count if retry_count is not None else Config.STASH_GRAPHQL_RETRY_COUNT
        self.retry_delay = retry_delay if retry_delay is not None else Config.STASH_GRAPHQL_RETRY_DELAY
        self._boxes_cache = None
        self._client = None  # 惰性初始化 httpx client

    async def _ensure_client(self):
        """确保 httpx AsyncClient 存在。"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)

    async def close(self):
        """关闭 httpx client。"""
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── 核心请求 ──────────────────────────────────────────────

    async def post(self, query, variables=None):
        """发送 GraphQL 请求，返回 data 或 None。

        重试策略（指数退避，retry_delay * 尝试次数）：
        - 传输层失败（断连/超时/HTTP 5xx/响应非 JSON）自动重试
        - GraphQL 业务错误（响应内 errors 字段）不重试，直接返回 None
        """
        await self._ensure_client()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["ApiKey"] = self.api_key
        payload = {"query": query}
        if variables is not None:
            payload["variables"] = variables

        for attempt in range(1, self.retry_count + 1):
            try:
                resp = await self._client.post(
                    self.stash_url, json=payload, headers=headers
                )
                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        "GraphQL HTTP %d" % resp.status_code,
                        request=resp.request, response=resp,
                    )
                data = resp.json()
                if "errors" in data:
                    logger.error("❌ GraphQL 错误: %s", data["errors"])
                    return None
                return data.get("data")
            except (httpx.TransportError, httpx.HTTPStatusError, ValueError) as e:
                if attempt < self.retry_count:
                    wait = self.retry_delay * attempt
                    logger.warning(
                        "⚠️ GraphQL 请求失败 (%d/%d): %s | %ss 后重试",
                        attempt, self.retry_count, str(e)[:200], wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                logger.error(
                    "❌ GraphQL 请求最终失败（%d 次重试后）: %s",
                    self.retry_count, str(e)[:300],
                )
                return None
        return None

    # ── stash-box 配置查询 ──────────────────────────────────

    async def get_stash_boxes(self):
        """查询 Stash 配置中的 stash-box 列表（按顺序返回 endpoint 列表）。"""
        if self._boxes_cache is not None:
            return self._boxes_cache
        query = """
        query GetStashBoxesOrder {
          configuration {
            general {
              stashBoxes { name endpoint }
            }
          }
        }
        """
        data = await self.post(query, {})
        if data:
            boxes = (
                data.get("configuration", {})
                .get("general", {})
                .get("stashBoxes", [])
            )
            self._boxes_cache = [b["endpoint"] for b in boxes]
            return self._boxes_cache
        return []

    async def get_endpoint(self, stash_box_index=0):
        """根据 index 从服务器配置获取 stash-box endpoint。"""
        boxes = await self.get_stash_boxes()
        if stash_box_index < len(boxes):
            return boxes[stash_box_index]
        return "https://stashdb.org/graphql"

    async def resolve_stash_box_index(self, scene_info, default=0):
        """根据场景已有的 stash_ids 自动解析 stash-box index。"""
        stash_ids = (scene_info or {}).get("stash_ids", [])
        if not stash_ids:
            return default
        endpoint = stash_ids[0]["endpoint"]
        boxes = await self.get_stash_boxes()
        for i, ep in enumerate(boxes):
            if ep == endpoint:
                return i
        return default

    async def resolve_stash_box_index_by_endpoint(self, endpoint_url, default=0):
        """根据 stash-box endpoint URL 查找对应的 Stash 配置索引。"""
        boxes = await self.get_stash_boxes()
        for i, ep in enumerate(boxes):
            if ep == endpoint_url:
                return i
        logger.warning(
            "⚠️ 未找到 endpoint %s 对应的 stash-box 配置，使用默认 %d",
            endpoint_url, default,
        )
        return default

    def invalidate_boxes_cache(self):
        self._boxes_cache = None
