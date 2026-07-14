"""路径映射 - 将 Stash 本地文件路径转换为 Alist 虚拟路径"""
import logging
from typing import Optional

logger = logging.getLogger("stash2alist.path_mapper")


class PathMapper:
    """根据配置的映射规则，将本地路径前缀替换为 Alist 路径前缀"""

    def __init__(self, mappings: list[dict]):
        self.mappings = sorted(mappings, key=lambda m: len(m["local"]), reverse=True)

    def to_alist_path(self, local_path: str) -> Optional[str]:
        """将本地路径转换为 Alist 路径，无匹配时返回 None"""
        for mapping in self.mappings:
            local_prefix = mapping["local"]
            alist_prefix = mapping["alist"]
            if not local_path.startswith("/"):
                local_path = "/" + local_path
            if local_path.startswith(local_prefix):
                remaining = local_path[len(local_prefix):]
                if not remaining.startswith("/"):
                    remaining = "/" + remaining
                result = alist_prefix.rstrip("/") + remaining
                filename = result.rsplit("/", 1)[-1] if "/" in result else result
                logger.info(f"路径映射 -> {result}")
                return result
        logger.warning(f"路径未匹配: {local_path}")
        return None
