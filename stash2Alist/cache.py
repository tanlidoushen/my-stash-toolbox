"""简单的 TTL 缓存（异步安全）"""
import time
import asyncio
from collections import OrderedDict


class TTLCache:
    """基于 OrderedDict 的 TTL 缓存（异步安全），自动淘汰过期条目"""

    def __init__(self, maxsize: int = 1000):
        self.maxsize = maxsize
        self._store: OrderedDict[str, tuple[float, object]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str):
        """获取缓存值，已过期返回 None"""
        async with self._lock:
            if key not in self._store:
                return None
            expire_ts, value = self._store[key]
            if time.time() < expire_ts:
                self._store.move_to_end(key)
                return value
            del self._store[key]
            return None

    async def set(self, key: str, value, ttl: int):
        """设置缓存值，ttl 单位为秒"""
        async with self._lock:
            if len(self._store) >= self.maxsize:
                self._store.popitem(last=False)
            self._store[key] = (time.time() + ttl, value)

    async def invalidate(self, key: str):
        """主动失效某个缓存条目"""
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self):
        """清空所有缓存"""
        async with self._lock:
            self._store.clear()
