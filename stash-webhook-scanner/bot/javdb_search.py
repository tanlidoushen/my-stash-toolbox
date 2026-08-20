"""JavDB 番号搜索 — 入口模块（re-export）。

实际实现已拆分到子模块：
  - javdb_search_state     → 全局状态 / 缓存 / 自动删除
  - javdb_search_utils      → 工具函数（图片 URL、封面下载）
  - javdb_search_format     → 格式化 / 展示
  - javdb_search_offline    → 离线任务监控
  - javdb_search_handlers   → 命令/回调处理器
"""

from bot.javdb_search_handlers import (
    cmd_javdb_search,
    handle_javdb_detail,
    handle_magnet_add,
    handle_magnet_dir_pick,
    handle_magnet_page,
)
from bot.javdb_search_offline import (
    handle_monitor_check,
    handle_monitor_close,
)

__all__ = [
    "cmd_javdb_search",
    "handle_javdb_detail",
    "handle_magnet_page",
    "handle_magnet_add",
    "handle_magnet_dir_pick",
    "handle_monitor_check",
    "handle_monitor_close",
]
