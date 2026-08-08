"""扫描操作：简单扫描、详细扫描、作业等待。

当调用方传入 ws_subscriber 时优先通过 WebSocket 订阅实时获取任务状态；
未传入时走纯 HTTP 轮询。
"""

import asyncio
import logging
from typing import Optional

from stash import query as Q
from stash.ws_subscriber import StashWSSubscriber

logger = logging.getLogger(__name__)


async def scan_simple(client, scan_paths):
    """简单扫描（仅路径）。返回 job_id 或 None。"""
    variables = {"input": {"paths": scan_paths}}
    data = await client.post(Q.METADATA_SCAN, variables)
    if data is None:
        return None
    job_id = data["metadataScan"]
    logger.info("      - 🚀 扫描任务已提交 | 任务ID=%s", job_id)
    return job_id


async def scan_detailed(client, scan_paths):
    """详细扫描（含预览、指纹、缩略图等）。返回 job_id 或 None。"""
    variables = {
        "input": {
            "paths": scan_paths,
            "rescan": True,
            "scanGenerateCovers": False,
            "scanGeneratePreviews": True,
            "scanGenerateImagePreviews": True,
            "scanGenerateSprites": True,
            "scanGeneratePhashes": True,
            "scanGenerateThumbnails": True,
            "scanGenerateClipPreviews": True,
        }
    }
    data = await client.post(Q.METADATA_SCAN, variables)
    if data is None:
        return None
    job_id = data["metadataScan"]
    logger.info("      - 🚀 扫描任务已提交 | 任务ID=%s", job_id)
    return job_id


async def get_job_status(client, job_id):
    """查询任务状态。返回状态字典或 None。"""
    data = await client.post(Q.FIND_JOB, {"input": {"id": str(job_id)}})
    if data is None:
        return None
    return data["findJob"]


async def get_job_queue(client):
    """查询 Stash 任务队列。返回任务列表或 None。"""
    data = await client.post(Q.JOB_QUEUE, {})
    if data is None:
        return None
    return data.get("jobQueue")


async def _find_job(client, job_id):
    """查询单个任务状态，区分网络错误和任务被遗忘。
    返回 (exists, status_dict):
      exists=False  -> 任务已被 Stash 遗忘
      status=None   -> 查询出错
      exists=True   -> 正常返回状态字典。
    """
    data = await client.post(Q.FIND_JOB, {"input": {"id": str(job_id)}})
    if data is None:
        return True, None
    job = data.get("findJob")
    if job is None:
        return False, None
    return True, job


async def wait_for_job_ws(ws_subscriber, job_id, timeout=None):
    """通过 WebSocket 订阅等待任务完成（新方式）。"""
    from config import Config
    if timeout is None:
        timeout = getattr(Config, "WS_JOB_TIMEOUT", 600)
    logger.info("         - ⏳ [WS] 等待任务 %s 完成...", job_id)
    result = await ws_subscriber.wait_job(str(job_id), timeout=timeout)
    if result is None:
        logger.warning("         - ⏭️ [WS] 任务 %s 等待超时或连接断开", job_id)
        return None
    s = result.get("status", "UNKNOWN")
    p = result.get("progress")
    logger.info("         - 📊 [WS] 任务 %s | 状态=%s | 进度=%s", job_id, s, p)
    if s == "FINISHED":
        logger.info("         - ✅ [WS] 任务 %s 已完成！", job_id)
    elif s in ("FAILED", "CANCELLED"):
        logger.warning("         - ❌ [WS] 任务 %s 已结束(%s): %s", job_id, s, result.get("error", "未知"))
    return result


async def wait_for_job(client, job_id, poll_interval=3,
                       ws_subscriber: Optional[StashWSSubscriber] = None):
    """等待任务完成。

    若传入 ws_subscriber 且连接正常，优先走 WebSocket 推送；
    WS 失败 / 超时自动降级到 HTTP 轮询。
    """
    from config import Config

    # ── 尝试 WebSocket 方式 ──────────────────────────────
    if ws_subscriber is not None and ws_subscriber.is_connected:
        try:
            result = await wait_for_job_ws(ws_subscriber, job_id)
            if result is not None:
                return result
            logger.warning("         - ⚠️ [WS] 返回 None，降级到 HTTP 轮询")
        except Exception as e:
            logger.warning("         - ⚠️ [WS] 异常(%s)，降级到 HTTP 轮询", e)

    # ── HTTP 轮询（原逻辑） ──────────────────────────────
    logger.info("         - ⏳ 等待任务 %s 完成...", job_id)

    # Phase 1: 通过 jobQueue 查询
    for i in range(6):  # 最多 6 轮，每轮 poll_interval 秒
        queue = await get_job_queue(client)
        if queue is not None:
            job = next((j for j in queue if j["id"] == str(job_id)), None)
            if job is not None:
                s = job["status"]
                p = job.get("progress")
                logger.info("         - 📊 任务 %s | 状态=%s | 进度=%s", job_id, s, p)
                if s == "FINISHED":
                    logger.info("         - ✅ 任务 %s 已完成！", job_id)
                    return job
                if s in ("FAILED", "CANCELLED"):
                    err = job.get("error", "未知")
                    logger.warning("         - ❌ 任务 %s 已结束(%s): %s", job_id, s, err)
                    return job
                await asyncio.sleep(poll_interval)
                continue
            logger.info("         - 🔄 任务 %s 已离开队列，切换至 findJob 查询", job_id)
            break
        else:
            logger.info("         - 🔄 jobQueue 查询失败，切换至 findJob 查询")
            break

    # Phase 2: 通过 findJob 查询
    while True:
        found, status = await _find_job(client, job_id)
        if not found:
            logger.warning("         - ⏭️ 任务 %s 已被 Stash 遗忘，跳过", job_id)
            return None
        if status is None:
            logger.warning("         - ⚠️ 查询任务 %s 状态失败，稍后重试", job_id)
            await asyncio.sleep(poll_interval)
            continue

        s = status["status"]
        p = status.get("progress")
        logger.info("         - 📊 任务 %s | 状态=%s | 进度=%s", job_id, s, p)
        if s == "FINISHED":
            logger.info("         - ✅ 任务 %s 已完成！", job_id)
            return status
        if s in ("FAILED", "CANCELLED"):
            err = status.get("error", "未知")
            logger.warning("         - ❌ 任务 %s 已结束(%s): %s", job_id, s, err)
            return status
        await asyncio.sleep(poll_interval)


async def wait_for_job_running_ws(ws_subscriber, job_id, timeout=None):
    """通过 WebSocket 订阅等待任务开始运行（新方式）。"""
    from config import Config
    if timeout is None:
        timeout = getattr(Config, "WS_JOB_TIMEOUT", 300)
    logger.info("         - ⏳ [WS] 等待任务 %s 开始运行...", job_id)
    result = await ws_subscriber.wait_job_running(str(job_id), timeout=timeout)
    if result is None:
        logger.warning("         - ⏭️ [WS] 任务 %s 等待超时或连接断开", job_id)
        return None
    s = result.get("status", "UNKNOWN")
    p = result.get("progress")
    logger.info("         - 📊 [WS] 任务 %s | 状态=%s | 进度=%s", job_id, s, p)
    if s in ("RUNNING", "FINISHED"):
        logger.info("         - ✅ [WS] 任务 %s 已开始运行", job_id)
    elif s in ("FAILED", "CANCELLED"):
        logger.warning("         - ❌ [WS] 任务 %s 已结束(%s): %s", job_id, s, result.get("error", "未知"))
    return result


async def wait_for_job_running(client, job_id, poll_interval=3,
                               ws_subscriber: Optional[StashWSSubscriber] = None):
    """等待任务开始运行（状态不再是 READY）。

    若传入 ws_subscriber 且连接正常，优先走 WebSocket 推送；
    WS 失败 / 超时自动降级到 HTTP 轮询。
    """
    logger.info("         - ⏳ 等待任务 %s 开始运行...", job_id)

    # ── 尝试 WebSocket 方式 ──────────────────────────────
    if ws_subscriber is not None and ws_subscriber.is_connected:
        try:
            result = await wait_for_job_running_ws(ws_subscriber, job_id)
            if result is not None:
                return result
            logger.warning("         - ⚠️ [WS] 返回 None，降级到 HTTP 轮询")
        except Exception as e:
            logger.warning("         - ⚠️ [WS] 异常(%s)，降级到 HTTP 轮询", e)

    # ── HTTP 轮询（原逻辑） ──────────────────────────────
    logger.info("         - 🔄 使用 HTTP 轮询等待任务 %s ...", job_id)
    while True:
        status = await get_job_status(client, job_id)
        if status is None:
            logger.warning("         - ⚠️ 查询任务 %s 状态失败，稍后重试", job_id)
            await asyncio.sleep(poll_interval)
            continue
        s = status["status"]
        p = status.get("progress")
        logger.info("         - 📊 任务 %s | 状态=%s | 进度=%s", job_id, s, p)
        if s in ("RUNNING", "FINISHED"):
            logger.info("         - ✅ 任务 %s 已开始运行", job_id)
            return status
        if s in ("FAILED", "CANCELLED"):
            err = status.get("error", "未知")
            logger.warning("         - ❌ 任务 %s 已结束(%s): %s", job_id, s, err)
            return status
        await asyncio.sleep(poll_interval)
