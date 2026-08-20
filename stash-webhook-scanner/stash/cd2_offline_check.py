# -*- coding: utf-8 -*-
"""CD2 离线任务查询：通过 ListAllOfflineFiles 按 infoHash 查找任务状态。"""

import asyncio
import logging

from config import Config
from cd2 import get_cd2_client

logger = logging.getLogger(__name__)

# protobuf 枚举 int → 字符串名（与旧封装/grpcurl JSON 一致）
_OFFLINE_STATUS_NAMES = {
    0: "OFFLINE_INIT",
    1: "OFFLINE_DOWNLOADING",
    2: "OFFLINE_FINISHED",
    3: "OFFLINE_ERROR",
    4: "OFFLINE_UNKNOWN",
}

# 离线任务查询需要 cloudName + cloudAccountId（新 proto 必填），惰性缓存
_cloud_key_cache = None


def _get_offline_cloud_key():
    """获取离线任务所属云盘标识 (cloudName, cloudAccountId)。

    从 GetAllCloudApis 中找第一个 115 云盘（离线下载主力盘），
    找不到则取第一个云盘。结果缓存。
    """
    global _cloud_key_cache
    if _cloud_key_cache is not None:
        return _cloud_key_cache
    client = get_cd2_client()
    result = client.GetAllCloudApis()
    apis = list(result.apis or [])
    chosen = None
    for api in apis:
        if "115" in (api.name or ""):
            chosen = api
            break
    if chosen is None and apis:
        chosen = apis[0]
    if chosen is None:
        return None
    _cloud_key_cache = (chosen.name, chosen.userName)
    return _cloud_key_cache


def _offline_to_dict(t):
    """ListAllOfflineFiles 的 protobuf OfflineFile → dict（camelCase，与旧版一致）。"""
    return {
        "name": t.name,
        "size": str(t.size),
        "url": t.url,
        "status": _OFFLINE_STATUS_NAMES.get(t.status, str(t.status)),
        "infoHash": t.infoHash,
        "fileId": t.fileId,
        "parentId": t.parentId,
        "percendDone": t.percendDone,
    }


async def _call_list_offline_files(page=1, path=None, timeout=30):
    """调用 CD2 ListAllOfflineFiles API（gRPC，异步线程池执行）。"""
    try:
        def _do():
            key = _get_offline_cloud_key()
            if key is None:
                return None
            result = get_cd2_client().ListAllOfflineFiles({
                "page": page,
                "path": path,
                "cloudName": key[0],
                "cloudAccountId": key[1],
            })
            return {
                "offlineFiles": [_offline_to_dict(t) for t in result.offlineFiles],
                "pageCount": result.pageCount,
            }
        return await asyncio.to_thread(_do)
    except asyncio.TimeoutError:
        logger.error("[CD2离线查询] 第%d页 超时", page)
        return None
    except Exception as e:
        logger.error("[CD2离线查询] 第%d页 异常: %s", page, e)
        return None


def _format_size(size_str):
    """将字节字符串转换为可读大小。"""
    try:
        size = int(size_str)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return "%.2f %s" % (size, unit)
            size /= 1024.0
        return "%.2f PB" % size
    except (ValueError, TypeError):
        return size_str


STATUS_TEXT = {
    "OFFLINE_DOWNLOADING": "下载中",
    "OFFLINE_FINISHED": "已完成",
    "OFFLINE_COMPLETED": "已完成",
    "OFFLINE_ERROR": "错误",
    "OFFLINE_PENDING": "等待中",
    "OFFLINE_PAUSED": "已暂停",
    "OFFLINE_CANCELLED": "已取消",
    "OFFLINE_WAITING": "等待中",
}


def _get_status_text(status):
    """获取状态中文描述。"""
    return STATUS_TEXT.get(status, status)


async def query_offline_task_by_hash(info_hash, path=None):
    """按 infoHash 分页查询 CD2 离线任务列表，返回匹配的任务信息字典。

    Args:
        info_hash: 磁力 infoHash（40 位十六进制字符串）

    Returns:
        dict 或 None:
            {
                "name": str,
                "status": str,        # 原始状态值，如 OFFLINE_DOWNLOADING
                "status_text": str,   # 中文状态，如 "下载中"
                "progress": float,    # 0.0 ~ 100.0
                "size": str,          # 格式化后的大小，如 "5.06 GB"
                "size_raw": str,      # 原始字节数字符串
                "folder": str,        # 目标目录（从 parentId 推断或返回请求的 path）
                "info_hash": str,
                "file_id": str,
                "url": str,
                "is_finished": bool,
                "is_error": bool,
            }
    """
    max_pages = Config.CD2_OFFLINE_CHECK_MAX_PAGES

    for page in range(1, max_pages + 1):
        data = await _call_list_offline_files(page=page, path=path)
        if not data:
            logger.warning("[CD2离线查询] 第%d页无数据，停止翻页", page)
            return None

        files = data.get("offlineFiles", [])
        if not files:
            logger.info("[CD2离线查询] 第%d页无任务，infoHash=%s", page, info_hash)
            return None

        for task in files:
            task_hash = task.get("infoHash", "")
            if task_hash and task_hash.lower() == info_hash.lower():
                # 找到匹配任务
                status = task.get("status", "")
                percend_done = task.get("percendDone", 0)
                try:
                    progress = float(percend_done)
                except (ValueError, TypeError):
                    progress = 0.0
                progress = max(0.0, min(100.0, progress))

                is_finished = status in ("OFFLINE_FINISHED", "OFFLINE_COMPLETED")
                is_error = status == "OFFLINE_ERROR"

                return {
                    "name": task.get("name", ""),
                    "status": status,
                    "status_text": _get_status_text(status),
                    "progress": progress,
                    "size": _format_size(task.get("size", "0")),
                    "size_raw": task.get("size", "0"),
                    "folder": task.get("parentId", ""),
                    "info_hash": task_hash,
                    "file_id": task.get("fileId", ""),
                    "url": task.get("url", ""),
                    "is_finished": is_finished,
                    "is_error": is_error,
                }

        # 检查是否还有下一页
        page_count = data.get("pageCount", 0)
        if page >= page_count:
            logger.info("[CD2离线查询] 已查完所有%d页，未找到 infoHash=%s", page_count, info_hash)
            return None

    logger.info("[CD2离线查询] 超过最大查询页数%d，未找到 infoHash=%s", max_pages, info_hash)
    return None
