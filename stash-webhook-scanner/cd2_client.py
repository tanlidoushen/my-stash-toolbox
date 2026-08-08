"""CD2 gRPC 统一客户端 —— grpcio 持久连接替代 grpcurl 子进程。

mover 搬移 / 场景删除 / 离线下载 / 离线任务查询 全部复用同一个长连接，
避免每次调用拉起一个 grpcurl 子进程。

返回的 dict 字段名与旧版 grpcurl JSON 输出保持一致（camelCase），
调用方无需改动。
"""

import logging
import threading

import grpc

import clouddrive_pb2 as pb
import clouddrive_pb2_grpc as pb_grpc
from config import Config

logger = logging.getLogger(__name__)

# 与旧版 grpcurl JSON 输出保持一致的字段名
_FILE_KEYS = ("id", "name", "fullPathName", "size", "isDirectory")
_OFFLINE_KEYS = (
    "name", "size", "url", "status",
    "infoHash", "fileId", "parentId", "percendDone",
)

# protobuf 枚举在 Python 中是 int，映射回与 grpcurl JSON 输出一致的枚举名字
# （否则下游按 "OFFLINE_FINISHED" 等名字判断状态会全部失效）
_OFFLINE_STATUS_NAMES = {
    0: "OFFLINE_INIT",
    1: "OFFLINE_DOWNLOADING",
    2: "OFFLINE_FINISHED",
    3: "OFFLINE_ERROR",
    4: "OFFLINE_UNKNOWN",
}


def _file_to_dict(f):
    return {k: getattr(f, k) for k in _FILE_KEYS}


def _offline_to_dict(t):
    d = {k: getattr(t, k) for k in _OFFLINE_KEYS}
    status = d.get("status")
    if isinstance(status, int) and status in _OFFLINE_STATUS_NAMES:
        d["status"] = _OFFLINE_STATUS_NAMES[status]
    return d


def _op_result_to_dict(r):
    return {"success": r.success, "errorMessage": r.errorMessage}


class CD2Client:
    """基于 grpcio 持久 channel 的 CloudDrive2 客户端（线程安全）。"""

    def __init__(self, server, token, timeout=60):
        self._server = server
        self._token = token
        self._timeout = timeout
        self._channel = None
        self._stub = None

    # ── 连接管理 ──────────────────────────────────────────────

    def _ensure_connected(self):
        if self._stub is None:
            self._channel = grpc.insecure_channel(self._server)
            self._stub = pb_grpc.CloudDriveFileSrvStub(self._channel)
        return self._stub

    @property
    def _metadata(self):
        return (("authorization", "Bearer %s" % self._token),)

    def close(self):
        if self._channel is not None:
            self._channel.close()
        self._channel = None
        self._stub = None

    def _call(self, method, req, timeout=None):
        """执行单个 gRPC 调用，统一把 RpcError 包装为 RuntimeError。"""
        stub = self._ensure_connected()
        try:
            return getattr(stub, method)(
                req,
                metadata=self._metadata,
                timeout=timeout if timeout is not None else self._timeout,
            )
        except grpc.RpcError as e:
            # 提取 details() 拿到干净的业务错误信息（如 115 的 "任务已存在"），
            # 避免把整个 _InactiveRpcError repr（含尖括号）传出去
            detail = ""
            try:
                detail = e.details() or ""
            except Exception:
                detail = ""
            raise RuntimeError("gRPC 调用失败 [%s]: %s" % (method, detail or e))

    # ── 文件操作 ──────────────────────────────────────────────

    def get_sub_files(self, path, force_refresh=False):
        """获取目录下所有子文件和子目录。"""
        req = pb.ListSubFileRequest(path=path, forceRefresh=force_refresh)
        files = []
        for resp in self._call("GetSubFiles", req):
            files.extend(_file_to_dict(f) for f in resp.subFiles)
        return files

    def get_file_info(self, path):
        """通过路径获取文件/目录信息（FindFileByPath）。"""
        req = pb.FindFileByPathRequest(parentPath="/", path=path)
        info = self._call("FindFileByPath", req)
        return _file_to_dict(info) if info else None

    def list_directory(self, path, force_refresh=False):
        """递归遍历整个目录，返回所有文件（平铺列表）。"""
        all_files = []
        stack = [path]
        visited = set()
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            try:
                entries = self.get_sub_files(current, force_refresh=force_refresh)
            except Exception as e:
                logger.warning("遍历失败（跳过）: %s — %s", current, e)
                continue
            for entry in entries:
                if entry.get("isDirectory"):
                    sub_path = entry.get("fullPathName") or entry.get("name", "")
                    if sub_path and sub_path not in visited:
                        stack.append(sub_path)
                else:
                    all_files.append(entry)
        return all_files

    def ensure_dir(self, directory_path):
        """递归确保目录存在，不存在则逐级创建。"""
        import os as _os

        directory_path = directory_path.rstrip("/")
        if not directory_path or directory_path == "/":
            return True
        try:
            self._call("GetSubFiles", pb.ListSubFileRequest(
                path=directory_path, forceRefresh=False))
            return True
        except Exception:
            pass
        parent = _os.path.dirname(directory_path).replace("\\", "/")
        folder_name = _os.path.basename(directory_path)
        if not self.ensure_dir(parent):
            return False
        try:
            self._call("CreateFolder", pb.CreateFolderRequest(
                parentPath=parent, folderName=folder_name))
            return True
        except Exception as e:
            logger.error("创建目录失败: %s — %s", directory_path, e)
            return False

    def move_file(self, source_paths, dest_path, conflict_policy=1):
        """批量移动文件。conflict_policy: 0=覆盖, 1=重命名, 2=跳过。"""
        self._call("MoveFile", pb.MoveFileRequest(
            theFilePaths=list(source_paths),
            destPath=dest_path,
            conflictPolicy=conflict_policy,
        ))

    def delete_file(self, path, force_refresh=False):
        """删除单个文件/目录。返回 {"success": bool, "errorMessage": str}。"""
        result = self._call("DeleteFile", pb.FileRequest(
            path=path, forceRefresh=force_refresh))
        return _op_result_to_dict(result)

    def delete_files(self, paths):
        """批量删除。返回 {"success": bool, "errorMessage": str}。"""
        result = self._call("DeleteFiles", pb.MultiFileRequest(path=list(paths)))
        return _op_result_to_dict(result)

    def search_file(self, path, search_term, force_refresh=True):
        """按内容搜索文件。"""
        req = pb.SearchRequest(
            path=path, searchFor=search_term,
            forceRefresh=force_refresh, contentSearch=True,
        )
        files = []
        for resp in self._call("GetSearchResults", req):
            files.extend(_file_to_dict(f) for f in resp.subFiles)
        return files

    # ── 离线下载 ──────────────────────────────────────────────

    def add_offline_files(self, urls, to_folder, timeout=30):
        """添加磁力离线下载任务。返回 {"success": bool, "errorMessage": str}。"""
        result = self._call("AddOfflineFiles", pb.AddOfflineFileRequest(
            urls=urls, toFolder=to_folder), timeout=timeout)
        return _op_result_to_dict(result)

    def list_all_offline_files(self, page=1, path=None, timeout=30):
        """分页查询离线任务列表。返回 {"offlineFiles": [...], "pageCount": int}。"""
        req = pb.OfflineFileListAllRequest(page=page, path=path)
        result = self._call("ListAllOfflineFiles", req, timeout=timeout)
        return {
            "offlineFiles": [_offline_to_dict(t) for t in result.offlineFiles],
            "pageCount": result.pageCount,
        }


# ── 全局单例（所有模块共享一个长连接） ────────────────────────

_client = None
_client_lock = threading.Lock()


def get_cd2_client():
    """返回全局共享的 CloudDrive2 客户端（线程安全，惰性创建）。"""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = CD2Client(server=Config.CD2_SERVER, token=Config.CD2_TOKEN)
    return _client
