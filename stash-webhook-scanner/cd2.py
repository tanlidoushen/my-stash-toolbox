"""CD2 客户端工厂 —— 直接基于 python-clouddrive-client(内置 app/clouddrive/)。

2026-08-21 重构：废弃自研 cd2_client.py(grpcio 直连封装)，
改为直接调用内置的 python-clouddrive-client 包（proto v1.0.13, 226 RPC）。

用法：
    from cd2 import get_cd2_client
    client = get_cd2_client()          # 原生 CloudDriveClient（同步方法）
    resp = client.FindFileByPath({"parentPath": "/", "path": "/115"})
    files = [f for r in client.GetSubFiles({"path": "/", "forceRefresh": False}) for f in r.subFiles]

注意：
- CloudDriveClient 的 RPC 方法参数接受 dict 或 pb2 Message，返回 protobuf 对象
- 认证直接注入 Bearer token（CD2_TOKEN），不走用户名密码登录
- 每个 RPC 方法带 async_ 参数（默认 False=同步），本项目全部用同步调用
"""

import logging

from clouddrive import CloudDriveClient
from config import Config

logger = logging.getLogger(__name__)

_client = None


def get_cd2_client() -> CloudDriveClient:
    """返回全局共享的 CloudDriveClient（惰性创建，token 直注）。"""
    global _client
    if _client is None:
        origin = Config.CD2_SERVER
        if not origin.startswith(("http://", "https://")):
            origin = "http://" + origin
        _client = CloudDriveClient(origin=origin)
        # 直接注入 Bearer token（与旧 cd2_client.py 的 metadata 一致），
        # 无需调用 login()（login 需要用户名密码走 GetToken）
        _client.metadata[:] = [("authorization", "Bearer " + Config.CD2_TOKEN)]
        logger.info("CD2 客户端已创建 | server=%s", Config.CD2_SERVER)
    return _client
