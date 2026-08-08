"""WebSocket 订阅管理器 —— 通过 GraphQL Subscription 实时监听 Stash 任务状态。

优先使用 WebSocket 获取任务进度，替代 HTTP 轮询。
当 WS 连接失败或不可用时，由调用方（scanner.py）自动降级到 HTTP 轮询。

心跳检测：
- 通过 websockets 库的 ping_interval / pong_timeout 自动发送 ping 帧，
  真实检测连接活性，避免 TCP 半开连接 / 静默断连导致订阅卡死。
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── 延迟导入 gql（避免未安装时崩溃） ────────────────────────
_gql_available = True
try:
    from gql import Client, gql
    from gql.transport.websockets import WebsocketsTransport
except ImportError:
    _gql_available = False
    logger.warning("⚠️ gql[websockets] 未安装，WebSocket 订阅不可用，将使用 HTTP 轮询")

SUBSCRIPTION_QUERY = gql("""
subscription OnJobUpdate {
  jobsSubscribe {
    type
    job {
      id
      status
      description
      progress
      subTasks
      startTime
      endTime
      addTime
      error
    }
  }
}
""") if _gql_available else None


class StashWSSubscriber:
    """Stash 任务 WebSocket 订阅管理器。

    - 通过 ping_interval/pong_timeout 自动检测死连接（静默断连）
    - 维持到 Stash 的长连接
    - 实时缓存所有 job 状态
    - 支持按 job_id 等待特定状态
    """

    def __init__(self, ws_url: str, api_key: Optional[str] = None,
                 ping_interval: float = 30, pong_timeout: float = 10):
        self.ws_url = ws_url
        self.api_key = api_key
        self._ping_interval = ping_interval
        self._pong_timeout = pong_timeout
        self._jobs: dict[str, dict] = {}                # job_id -> latest job dict
        self._waiters: dict[str, list[asyncio.Future]] = {}  # job_id -> [futures]
        self._running_waiters: dict[str, list[asyncio.Future]] = {}  # 等待 RUNNING
        self._task: Optional[asyncio.Task] = None
        self._started = False
        self._connected = asyncio.Event()
        self._stop_event = asyncio.Event()

    # ── 生命周期 ──────────────────────────────────────────────

    async def start(self):
        """启动后台订阅任务。"""
        if not _gql_available:
            logger.warning("⚠️ gql 不可用，WS subscriber 无法启动")
            return
        if self._started:
            return
        self._started = True
        self._stop_event.clear()
        self._task = asyncio.ensure_future(self._run_loop())
        logger.info("📡 WS Subscriber 已启动 | 目标=%s | heartbeat=%ss/%ss",
                     self.ws_url, self._ping_interval, self._pong_timeout)

    async def stop(self):
        """停止后台订阅任务。"""
        self._stop_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._started = False
        self._connected.clear()
        # 取消所有等待者
        for futures in self._waiters.values():
            for f in futures:
                if not f.done():
                    f.cancel()
        for futures in self._running_waiters.values():
            for f in futures:
                if not f.done():
                    f.cancel()
        self._waiters.clear()
        self._running_waiters.clear()
        logger.info("📡 WS Subscriber 已停止")

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    # ── 等待接口 ──────────────────────────────────────────────

    async def wait_job(self, job_id: str, timeout: float = 600) -> Optional[dict]:
        """等待指定任务达到终态（FINISHED / FAILED / CANCELLED）。

        Returns:
            最终 job dict，或 None（超时/取消）
        """
        job_id = str(job_id)

        # 先检查缓存，看任务是否已经终态
        cached = self._jobs.get(job_id)
        if cached and cached.get("status") in ("FINISHED", "FAILED", "CANCELLED"):
            return cached

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._waiters.setdefault(job_id, []).append(future)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("⏱️ WS 等待任务 %s 超时(%ss)", job_id, timeout)
            return None
        except asyncio.CancelledError:
            return None
        finally:
            waiters = self._waiters.get(job_id, [])
            if future in waiters:
                waiters.remove(future)

    async def wait_job_running(self, job_id: str, timeout: float = 300) -> Optional[dict]:
        """等待指定任务进入 RUNNING / FINISHED / FAILED / CANCELLED。

        Returns:
            job dict，或 None（超时/取消）
        """
        job_id = str(job_id)

        cached = self._jobs.get(job_id)
        if cached and cached.get("status") in ("RUNNING", "FINISHED", "FAILED", "CANCELLED"):
            return cached

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._running_waiters.setdefault(job_id, []).append(future)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("⏱️ WS 等待任务 %s 运行超时(%ss)", job_id, timeout)
            return None
        except asyncio.CancelledError:
            return None
        finally:
            waiters = self._running_waiters.get(job_id, [])
            if future in waiters:
                waiters.remove(future)

    # ── 后台订阅循环 ─────────────────────────────────────────

    async def _run_loop(self):
        """带自动重连的 WebSocket 订阅循环。

        连接正常退出（如服务端 close）: 重置退避并重连
        连接异常: 记录错误 + 指数退避重连
        """
        backoff = 1
        while not self._stop_event.is_set():
            try:
                await self._connect_and_listen()
                # 正常退出（服务端主动断开 / 通道关闭），重置退避后重连
                self._connected.clear()
                logger.info("🔄 WS 连接正常关闭，%ss 后重连", backoff)
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=backoff)
                    break  # stop_event 被设置
                except asyncio.TimeoutError:
                    pass
                backoff = 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._connected.clear()
                logger.error("❌ WS 连接异常: %s | %ss 后重连", e, backoff)
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=backoff)
                    break  # stop_event 被设置
                except asyncio.TimeoutError:
                    pass
                backoff = min(backoff * 2, 30)  # 指数退避，最大 30s

    async def _connect_and_listen(self):
        """建立连接并监听 subscription 消息。"""
        headers = {}
        if self.api_key:
            headers["ApiKey"] = self.api_key

        transport = WebsocketsTransport(
            url=self.ws_url, headers=headers,
            ping_interval=self._ping_interval,
            pong_timeout=self._pong_timeout,
        )

        async with Client(transport=transport, fetch_schema_from_transport=False) as session:
            self._connected.set()
            logger.info("✅ WS 连接成功: %s", self.ws_url)

            async for result in session.subscribe(SUBSCRIPTION_QUERY):
                if self._stop_event.is_set():
                    break

                data = result.get("jobsSubscribe")
                if not data:
                    continue

                job = data.get("job", {})
                job_id = job.get("id")
                if not job_id:
                    continue

                # 更新缓存
                self._jobs[job_id] = job
                status = job.get("status", "UNKNOWN")
                progress = job.get("progress")

                logger.debug(
                    "📊 WS Job 更新 | id=%s status=%s progress=%s",
                    job_id, status, progress,
                )

                # 通知终态等待者
                if status in ("FINISHED", "FAILED", "CANCELLED"):
                    self._resolve_waiters(self._waiters, job_id, job)

                # 通知 RUNNING 等待者
                if status in ("RUNNING", "FINISHED", "FAILED", "CANCELLED"):
                    self._resolve_waiters(self._running_waiters, job_id, job)

    @staticmethod
    def _resolve_waiters(waiters_map: dict, job_id: str, job: dict):
        """唤醒所有等待该 job_id 的 future。"""
        futures = waiters_map.get(job_id, [])
        for f in futures[:]:
            if not f.done():
                f.set_result(job)
        # 清理已唤醒的
        if job_id in waiters_map:
            waiters_map[job_id] = [f for f in waiters_map[job_id] if not f.done()]
            if not waiters_map[job_id]:
                del waiters_map[job_id]
