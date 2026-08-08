"""请求去重：基于 MD5 的短时窗口去重，防止重复通知。"""

import hashlib
import time

_RECENT_DEDUP_SECONDS = 5
_recent_request_hashes = {}


def is_duplicate_request(body_bytes):
    """检查是否为重复请求（相同 body 在 _RECENT_DEDUP_SECONDS 内到达过）。"""
    now = time.time()
    req_hash = hashlib.md5(body_bytes).hexdigest()

    # 清理过期记录
    expired = [
        h for h, ts in _recent_request_hashes.items()
        if now - ts > _RECENT_DEDUP_SECONDS
    ]
    for h in expired:
        del _recent_request_hashes[h]

    if req_hash in _recent_request_hashes:
        return True
    _recent_request_hashes[req_hash] = now
    return False
