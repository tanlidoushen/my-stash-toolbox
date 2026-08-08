import os


class Config:

    # ╔══════════════════════════════════════════════════════════════╗
    # ║  必填配置 — 不配好服务无法正常运行                          ║
    # ╚══════════════════════════════════════════════════════════════╝

    # ── Stash 连接 ────────────────────────────────────────────────
    # Stash GraphQL API 地址（必填）
    STASH_URL = os.environ.get("STASH_URL", "http://<stash-server>:9999/graphql")
    # Stash API Key（如果 Stash 开启了 ApiKey 认证）
    STASH_APIKEY = os.environ.get('STASH_APIKEY', '')
    # Stash 基础 URL（用于生成播放、演员、工作室等超链接）
    STASH_BASE_URL = os.environ.get("STASH_BASE_URL", "http://<stash-proxy>:9997")

    # ── Flask 监听 ────────────────────────────────────────────────
    FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.environ.get("FLASK_PORT", "9991"))

    # ── CloudDrive2 gRPC ──────────────────────────────────────────
    # CD2 gRPC 地址（格式: host:port）
    CD2_SERVER = os.environ.get("CD2_SERVER", "<cd2-server>:19798")
    # CD2 访问令牌
    CD2_TOKEN = os.environ.get("CD2_TOKEN", "")
    # 文件路径前缀裁剪（Stash 真实路径 → CD2 虚拟路径转换时去掉此前缀）
    CD2_STRIP_PREFIX = os.environ.get("CD2_STRIP_PREFIX", "/local/mount")

    # ── 路径映射 ──────────────────────────────────────────────────
    # Webhook 通知中的 CloudDrive 路径 → Stash 实际挂载路径的映射
    # 格式: ((旧前缀, 新前缀), ...)
    PATH_PREFIX_MAP = (
        ("/cloud", "/local/mount/cloud"),
    )

    # ── 文件过滤 ──────────────────────────────────────────────────
    # 允许触发扫描的文件后缀
    ALLOWED_EXTENSIONS = {".mkv", ".mp4", ".avi", ".rmvb"}
    # Webhook 推送的路径中必须包含的关键词（用于过滤无关文件）
    ALLOWED_KEYWORDS = {"/path/to/media"}

    # ── 插件目录 ──────────────────────────────────────────────────
    # 刮削插件自动发现目录（存放 *_plugin.py）
    PLUGIN_DIR = os.environ.get("PLUGIN_DIR", os.path.join(os.path.dirname(__file__), "plugins"))


    # ╔══════════════════════════════════════════════════════════════╗
    # ║  重要配置 — 有默认值，但建议按实际环境调整                   ║
    # ╚══════════════════════════════════════════════════════════════╝

    # ── JAV / Non-JAV 识别 ────────────────────────────────────────
    # 目录路径规则映射：根据 source/dest 路径前缀判断 JAV/Non-JAV
    # 优先级高于文件名检测；未命中时 fallback 到原有逻辑
    DIR_JAV_RULES = [
        # 示例：jav-incoming → classified = JAV
        {"source_prefix": "/path/to/jav-incoming",
         "dest_prefix":   "/path/to/classified",
         "is_jav": True},
        # 示例：nonjav-incoming → classified = Non-JAV
        {"source_prefix": "/path/to/nonjav-incoming",
         "dest_prefix":   "/path/to/classified",
         "is_jav": False},
    ]
    # 番号前缀黑名单：匹配到的前缀视为 Non-JAV（欧美工作室代码）
    WESTERN_CODE_BLACKLIST = {
        "WUNF", "EVIL", "JULES", "TUSHY", "TUSH", "VIXEN", "BLACKED",
        "DEEPER", "SLUT", "MOMS", "TEENS", "BANG", "BRAZZERS", "NAUGHTY",
    }

    # ── Telegram 通知 ─────────────────────────────────────────────
    # Telegram Bot Token（留空则不启用 Bot 和通知）
    TG_BOT_TOKEN = os.environ.get('TG_BOT_TOKEN', '')
    # 通知目标 Chat ID
    TG_CHAT_ID = os.environ.get('TG_CHAT_ID', '')
    # 消息所有者 User ID（用于自动消息回应和权限过滤）
    TG_OWNER_ID = int(os.environ.get('TG_OWNER_ID', '0'))

    # ── stash2alist 代理模式 ──────────────────────────────────────
    # stash2alist 模式切换 API 地址
    STASH2CD2_MODE_API = os.environ.get("STASH2CD2_MODE_API", "http://<stash-proxy>:9997/api/mode")

    # ── 文件搬移（归类） ──────────────────────────────────────────
    # 多规则搬移配置，每项支持：
    #   name              - 规则名称（日志用）
    #   monitor_path      - 监控目录
    #   video_dest_base   - 归类后目录
    #   trash_dest        - 待删除目录
    #   folder_prefix     - 分卷文件夹前缀
    #   max_files_per_folder - 每卷最大文件数
    #   small_file_size   - 小于此大小视为待删除（默认100MB）
    #   trash_keywords    - 文件名含这些关键词视为待删除
    #   cleanup_empty_dirs - 是否清理空目录
    MOVER_RULES = [
        {
            "name": "default",
            "monitor_path": "/path/to/monitor",
            "video_dest_base": "/path/to/classified",
            "trash_dest": "/path/to/trash",
            "folder_prefix": "folder",
            "max_files_per_folder": 2000,
            "small_file_size": 100 * 1024 * 1024,
            "trash_keywords": {"sample", "trailer"},
            "cleanup_empty_dirs": True,
        },
    ]
    # 搬移冲突策略: 0=覆盖, 1=自动重命名, 2=跳过
    CONFLICT_POLICY = int(os.environ.get("CONFLICT_POLICY", "1"))
    # 视频文件扩展名（搬移分类用）
    VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".m4v", ".ts"}


    # ╔══════════════════════════════════════════════════════════════╗
    # ║  调优配置 — 涉及等待时间、重试策略、调试开关等               ║
    # ╚══════════════════════════════════════════════════════════════╝

    # ── 防抖 ──────────────────────────────────────────────────────
    # Webhook 事件防抖等待时间（秒）：短时间内的多次变更合并处理
    DEBOUNCE_WAIT = int(os.environ.get("DEBOUNCE_WAIT", "10"))
    # 搬移模块独立防抖（秒）
    MOVER_DEBOUNCE_WAIT = int(os.environ.get("MOVER_DEBOUNCE_WAIT", "10"))

    # ── WebSocket 订阅 ────────────────────────────────────────────
    # WS 地址（留空则自动从 STASH_URL 推导: http→ws）
    STASH_WS_URL = os.environ.get("STASH_WS_URL", "")
    # 是否启用 WebSocket 实时订阅（关闭则纯用 HTTP 轮询）
    WS_ENABLED = os.environ.get("WS_ENABLED", "").lower() in ("1", "true", "yes", "")
    # WS 等待任务超时（秒）
    WS_JOB_TIMEOUT = int(os.environ.get("WS_JOB_TIMEOUT", "600"))
    # WS 连接失败后是否自动降级到 HTTP 轮询
    WS_FALLBACK_HTTP = os.environ.get("WS_FALLBACK_HTTP", "").lower() in ("1", "true", "yes", "")

    # ── 重试 ──────────────────────────────────────────────────────
    # JAV 刮削重试次数
    JAV_SCRAPE_RETRY_COUNT = int(os.environ.get("JAV_SCRAPE_RETRY_COUNT", "3"))
    # JAV 刮削重试间隔（秒）
    JAV_SCRAPE_RETRY_DELAY = int(os.environ.get("JAV_SCRAPE_RETRY_DELAY", "5"))
    # Stash GraphQL 请求重试次数（仅传输层失败：断连/超时/HTTP 5xx）
    STASH_GRAPHQL_RETRY_COUNT = int(os.environ.get("STASH_GRAPHQL_RETRY_COUNT", "3"))
    # Stash GraphQL 请求重试间隔（秒）
    STASH_GRAPHQL_RETRY_DELAY = int(os.environ.get("STASH_GRAPHQL_RETRY_DELAY", "2"))

    # ── 消息自动删除 ──────────────────────────────────────────────
    # TG 搜索结果多少秒后自动删除，设为 0 关闭
    SEARCH_AUTO_DELETE_DELAY = int(os.environ.get("SEARCH_AUTO_DELETE_DELAY", "30"))
    # 归类启动消息自动删除（秒）
    CLASSIFY_START_AUTO_DELETE_DELAY = int(os.environ.get("CLASSIFY_START_AUTO_DELETE_DELAY", "10"))
    # 归类完成消息自动删除（秒）
    CLASSIFY_DONE_AUTO_DELETE_DELAY = int(os.environ.get("CLASSIFY_DONE_AUTO_DELETE_DELAY", "10"))

    # ── 调试 ──────────────────────────────────────────────────────
    # 开启后输出详细的文件变更通知等调试日志
    DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")


    # ╔══════════════════════════════════════════════════════════════╗
    @classmethod
    def get_mover_rules(cls):
        """返回有效的搬移规则列表。MOVER_RULES 非空则使用 MOVER_RULES，否则从旧配置构造单条规则。"""
        if cls.MOVER_RULES:
            return cls.MOVER_RULES
        return [
            {
                "name": "默认规则",
                "monitor_path": cls.MOVER_MONITOR_PATH or "/path/to/monitor",
                "video_dest_base": cls.MOVER_VIDEO_DEST_BASE or "/path/to/classified",
                "trash_dest": cls.MOVER_TRASH_DEST or "/path/to/trash",
                "folder_prefix": cls.MOVER_FOLDER_PREFIX,
                "max_files_per_folder": cls.MOVER_MAX_FILES_PER_FOLDER,
                "small_file_size": cls.MOVER_SMALL_FILE_SIZE,
                "trash_keywords": cls.MOVER_TRASH_KEYWORDS,
                "cleanup_empty_dirs": cls.MOVER_CLEANUP_EMPTY_DIRS,
            },
        ]
