# -*- coding: utf-8 -*-
"""CD2 离线下载：通过 gRPC 调用 AddOfflineFiles 添加磁力链接。"""

import asyncio
import logging

from config import Config
from cd2 import get_cd2_client

logger = logging.getLogger(__name__)


async def add_offline_download(magnet_url, to_folder=None):
    """调用 CD2 AddOfflineFiles 添加离线下载任务。

    Args:
        magnet_url: 磁力链接 (magnet:?xt=urn:btih:...)
        to_folder:  目标文件夹路径，默认使用 Config.CD2_OFFLINE_FOLDER

    Returns:
        (ok: bool, error_msg: str|None)
    """
    if not to_folder:
        to_folder = Config.CD2_OFFLINE_FOLDER

    try:
        data = await asyncio.to_thread(
            lambda: get_cd2_client().AddOfflineFiles(
                {"urls": magnet_url, "toFolder": to_folder}
            )
        )
        if data.success:
            logger.info("CD2 AddOfflineFiles 成功 -> %s", to_folder)
            return True, None
        err_msg = data.errorMessage or "未知错误"
        logger.error("CD2 AddOfflineFiles 返回失败: %s", err_msg)
        return False, err_msg

    except asyncio.TimeoutError:
        logger.error("CD2 AddOfflineFiles 超时 (30s)")
        return False, "请求超时"
    except Exception as e:
        logger.error("CD2 AddOfflineFiles 异常: %s", e)
        # 保留足够长度，确保下游能识别重复任务（115 code 10008 "任务已存在"）
        return False, str(e)[:300]
