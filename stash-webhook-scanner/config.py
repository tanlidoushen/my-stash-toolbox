import os


class Config:

    # ╔══════════════════════════════════════════════════════════════╗
    # ║  必填配置 — 不配好服务无法正常运行                          ║
    # ╚══════════════════════════════════════════════════════════════╝

    # ── Stash 连接 ────────────────────────────────────────────────
    # Stash GraphQL API 地址
    STASH_URL = os.environ.get("STASH_URL", "http://<stash-server>:9999/graphql")
    # Stash API Key（如果 Stash 配置了 ApiKey）
    STASH_APIKEY = os.environ.get('STASH_APIKEY', '')
    # Stash 基础 URL（用于生成播放、标签、演员、片商等超链接）
    STASH_BASE_URL = os.environ.get("STASH_BASE_URL", "http://<stash-proxy>:9997")

    # ── Flask 监听 ────────────────────────────────────────────────
    FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.environ.get("FLASK_PORT", "9991"))

    # ── CloudDrive2 gRPC ──────────────────────────────────────────
    # ⚠️ 旧版 grpcurl 子进程方式已废弃，统一走 cd2_client.py（grpcio 持久连接）
    # 以下三项仅兼容历史代码，不再被新代码使用
    CD2_GRPCURL = os.environ.get("CD2_GRPCURL", "")
    CD2_PROTO_PATH = os.environ.get("CD2_PROTO_PATH", "")
    CD2_PROTO_FILE = os.environ.get("CD2_PROTO_FILE", "clouddrive.proto")
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
        # 日影片目录 → 归类后 = JAV
        {"source_prefix": "/path/to/video-incoming",
         "dest_prefix":   "/path/to/classified",
         "is_jav": True},
        # 欧美影片目录 → 归类后 = Non-JAV
        {"source_prefix": "/path/to/nonjav-incoming",
         "dest_prefix":   "/path/to/classified",
         "is_jav": False},
    ]
    # 番号前缀黑名单：匹配到的前缀视为 Non-JAV（欧美工作室代码）
    WESTERN_CODE_BLACKLIST = {
        "WUNF", "EVIL", "JULES", "TUSHY", "TUSH", "VIXEN", "BLACKED",
        "DEEPER", "SLUT", "MOMS", "TEENS", "BANG", "BRAZZERS", "NAUGHTY",
    }

    # ── JAV 刮削 ──────────────────────────────────────────────────
    # javstash 端点（日本影片刮削用）
    JAV_STASH_BOX_ENDPOINT = os.environ.get("JAV_STASH_BOX_ENDPOINT", "https://javstash.org/graphql")

    # ── AVDB 聚合磁力 API ─────────────────────────────────────────
    # 磁力来源：AVDB 聚合搜索（色花堂/x1080x 等多站），磁力并入搜索详情页并置顶
    # 默认开启；失败时自动降级（仅记日志返回空）
    AVDB_API_ENABLED = os.environ.get("AVDB_API_ENABLED", "").lower() in ("1", "true", "yes", "")
    AVDB_API_URL = os.environ.get("AVDB_API_URL", "http://<avdb-server>:18000/api/v1/articles/torrents")
    AVDB_API_KEY = os.environ.get("AVDB_API_KEY", "")
    AVDB_API_TIMEOUT = int(os.environ.get("AVDB_API_TIMEOUT", "10"))
    # ── 磁力链接展示分组 ─────────────────────────────────────────
    # 来源体系顺序(逗号分隔,前=优先显示)。AVDB 系关键词:AVDB/色花堂/x1080x;JavDB 系:JavDB
    MAGNET_GROUP_ORDER = os.environ.get("MAGNET_GROUP_ORDER", "AVDB,JavDB")
    # 组内标签子组优先级(逗号分隔,前=优先)。磁力按首个匹配标签归类到子组
    MAGNET_TAG_PRIORITY = os.environ.get("MAGNET_TAG_PRIORITY", "中字,4K,高清")
    # 是否启用分组(0=关闭,恢复旧的全混排)
    MAGNET_GROUPING_ENABLED = os.environ.get("MAGNET_GROUPING_ENABLED", "1").lower() in ("1", "true", "yes", "on")
    # ── 磁力搜索自动选定 ─────────────────────────────────────────
    # /code 搜索影片后自动选定直接进详情(跳过候选列表)：1=开(默认) 0=关(恢复手动选)
    MAGNET_AUTO_PICK_ENABLED = os.environ.get("MAGNET_AUTO_PICK_ENABLED", "1").lower() in ("1", "true", "yes", "on")
    # 自动选定时优先使用的来源(逗号分隔按序)。该源有精确番号匹配则用它，
    # 否则回退其他源的精确匹配；全部无精确匹配(无法判断)才展示候选列表
    MAGNET_AUTO_PICK_PREFER = os.environ.get("MAGNET_AUTO_PICK_PREFER", "AVDB")
    # ── 校验码采集 ──────────────────────────────────────────────
    # 总开关：刮削写库后自动采集校验码落 SQLite（默认开）
    ENABLE_CHECKSUM = os.environ.get("ENABLE_CHECKSUM", "true").lower() in ("1", "true", "yes", "on")
    # ed2k 大小上限（字节；-1/<=0 = 无限制，用户定案 2026-08-17）
    ED2K_MAX_SIZE = int(os.environ.get("ED2K_MAX_SIZE", "-1"))
    # ed2k 流式计算超时（秒）
    ED2K_TIMEOUT = int(os.environ.get("ED2K_TIMEOUT", "600"))

    # ── Telegram 通知 ─────────────────────────────────────────────
    # Telegram Bot Token
    TG_BOT_TOKEN = os.environ.get('TG_BOT_TOKEN', '')
    # 通知目标 Chat ID
    TG_CHAT_ID = os.environ.get('TG_CHAT_ID', '')
    # 消息所有者 User ID（用于自动消息回应和权限过滤）
    TG_OWNER_ID = int(os.environ.get('TG_OWNER_ID', '0'))

    # theporndb 登录凭据（抓 performer 简介用；未配置则跳过简介抓取）
    TPDB_EMAIL = os.environ.get('TPDB_EMAIL', '')
    TPDB_PASSWORD = os.environ.get('TPDB_PASSWORD', '')
    TPDB_PROXY = os.environ.get('TPDB_PROXY', 'http://<proxy>:7890')

    # ── 标记同步 ────────────────────────────────────────────────────
    # Non-JAV 刮削流程中的双源标记同步（tt + TPDB）
    MARKER_SYNC_ENABLED = os.environ.get('MARKER_SYNC_ENABLED', 'true').lower() in ('1', 'true', 'yes')
    # 后缀功能：标记来源标签/标题前缀（对应原插件 addTsTradeTag/addTsTradeTitle/addTPDBMarkerTag/addTPDBMarkerTitle）
    MARKER_SYNC_TT_TAG = os.environ.get('MARKER_SYNC_TT_TAG', '').lower() in ('1', 'true', 'yes')
    MARKER_SYNC_TT_TITLE = os.environ.get('MARKER_SYNC_TT_TITLE', 'true').lower() in ('1', 'true', 'yes')
    MARKER_SYNC_TPDB_TAG = os.environ.get('MARKER_SYNC_TPDB_TAG', '').lower() in ('1', 'true', 'yes')
    MARKER_SYNC_TPDB_TITLE = os.environ.get('MARKER_SYNC_TPDB_TITLE', 'true').lower() in ('1', 'true', 'yes')
    # stash-box 统一代理（访问 stashdb/theporndb 指纹查库 + 标记同步外网请求）
    STASHBOX_PROXY = os.environ.get('STASHBOX_PROXY', 'http://<proxy>:7890')

    # ── 演员图库同步 ───────────────────────────────────────────
    # 场景刾刷完成后自动为演员同步 stash-box 图库（Gallery）
    PERFORMER_GALLERY_ENABLED = os.environ.get(
        "PERFORMER_GALLERY_ENABLED", "true"
    ).lower() in ("1", "true", "yes")
    # 图库下载路径（需与 stash-performer-gallery-cli 容器一致）
    PERFORMER_GALLERY_PATH = os.environ.get(
        "PERFORMER_GALLERY_PATH", "/path/to/performer-gallery"
    )
    # 额外跑 Stash URL 刾刷器（默认关闭——慢且收益低）
    PERFORMER_GALLERY_SCRAPER = os.environ.get(
        "PERFORMER_GALLERY_SCRAPER", "false"
    ).lower() in ("1", "true", "yes")
    # 额外爬 babepedia 图集（默认关闭——需 FlareSolverr）
    PERFORMER_GALLERY_BABEPEDIA = os.environ.get(
        "PERFORMER_GALLERY_BABEPEDIA", "false"
    ).lower() in ("1", "true", "yes")
    # 额外爬 indexxx 图集（默认关闭——需 FlareSolverr）
    PERFORMER_GALLERY_INDEXXX = os.environ.get(
        "PERFORMER_GALLERY_INDEXXX", "false"
    ).lower() in ("1", "true", "yes")
    # 处理的演员性别（逗号分隔，空=全部）
    PERFORMER_GALLERY_GENDERS = os.environ.get(
        "PERFORMER_GALLERY_GENDERS", "FEMALE,TRANSGENDER_FEMALE"
    ).split(",")


    # ── 演员图库同步 ──────────────────────────────────────────────
    # 场景刮剃完成后自动为演员同步 stash-box 图库\uff08Gallery\uff09
    PERFORMER_GALLERY_ENABLED = os.environ.get(
        "PERFORMER_GALLERY_ENABLED", "true"
    ).lower() in ("1", "true", "yes")
    # 图库下载路径\uff08需与 stash-performer-gallery-cli 容器一致\uff09
    PERFORMER_GALLERY_PATH = os.environ.get(
        "PERFORMER_GALLERY_PATH", "/path/to/performer-gallery"
    )
    # 额外跑 Stash URL 刮剃器\uff08默认关闭——慢且收益低\uff09
    PERFORMER_GALLERY_SCRAPER = os.environ.get(
        "PERFORMER_GALLERY_SCRAPER", "false"
    ).lower() in ("1", "true", "yes")
    # 额外爬 babepedia 图集\uff08默认关闭——需 FlareSolverr\uff09
    PERFORMER_GALLERY_BABEPEDIA = os.environ.get(
        "PERFORMER_GALLERY_BABEPEDIA", "false"
    ).lower() in ("1", "true", "yes")
    # 额外爬 indexxx 图集\uff08默认关闭——需 FlareSolverr\uff09
    PERFORMER_GALLERY_INDEXXX = os.environ.get(
        "PERFORMER_GALLERY_INDEXXX", "false"
    ).lower() in ("1", "true", "yes")

    # ── stash2alist 代理模式 ────────────────────────────────────────
    # stash2alist 模式切换 API 地址
    STASH2ALIST_MODE_API = os.environ.get("STASH2ALIST_MODE_API", "http://<stash2alist-server>:9997/api/mode")

    # ── CD2 离线下载 ──────────────────────────────────────────────
    # 磁力链接默认添加到此目录
    CD2_OFFLINE_FOLDER = os.environ.get("CD2_OFFLINE_FOLDER", "/path/to/video-incoming")
    # 磁力链接可选存储目录映射（格式：{"简称": "实际路径", ...}）
    # 通过环境变量设置时需传入 JSON 字符串，例如：
    #   export CD2_OFFLINE_FOLDERS='{"影片目录":"/path/a","待分类":"/path/b"}'
    CD2_OFFLINE_FOLDERS = os.environ.get("CD2_OFFLINE_FOLDERS", {
        "影片目录": "/path/to/video-incoming",
        "测试":   "/path/to/test",
        # 示例新增：
        # "待分类": "/path/to/pending",
        # "新片":   "/path/to/new",
    })

    # ── 文件搬移（归类） ──────────────────────────────────────────
    # 多规则搬移配置，每项支持：
    #   name              - 规则名称（日志用）
    #   monitor_path      - 监控目录
    #   video_dest_base   - 归类后目录
    #   trash_dest        - 待删除目录
    #   folder_prefix     - 分卷文件夹前缀（默认"目录"）
    #   max_files_per_folder - 每卷最大文件数（默认2000）
    #   small_file_size   - 小于此大小视为待删除（默认100MB）
    #   trash_keywords    - 文件名含这些关键词视为待删除
    #   cleanup_empty_dirs - 是否清理空目录
    MOVER_RULES = [
        {
            "name": "影片目录",
            "monitor_path": "/path/to/video-incoming",
            "video_dest_base": "/path/to/classified",
            "trash_dest": "/path/to/trash",
            "folder_prefix": "目录",
            "max_files_per_folder": 2000,
            "small_file_size": 100 * 1024 * 1024,
            "trash_keywords": {"trailer", "preview"},
            "cleanup_empty_dirs": True,
        },
        {
            "name": "欧美影片目录",
            "monitor_path": "/path/to/nonjav-incoming",
            "video_dest_base": "/path/to/classified",
            "trash_dest": "/path/to/trash",
            "folder_prefix": "目录",
            "max_files_per_folder": 2000,
            "small_file_size": 100 * 1024 * 1024,
            "trash_keywords": {"trailer", "preview"},
            "cleanup_empty_dirs": True,
        },
        {
            "name": "欧美影片目录",
            "monitor_path": "/path/to/avdb-incoming",
            "video_dest_base": "/path/to/classified",
            "trash_dest": "/path/to/trash",
            "folder_prefix": "目录",
            "max_files_per_folder": 2000,
            "small_file_size": 100 * 1024 * 1024,
            "trash_keywords": {"trailer", "preview"},
            "cleanup_empty_dirs": True,
        },
    ]
    # 搬移冲突策略: 0=覆盖, 1=自动重命名, 2=跳过（MoveFileRequest.ConflictPolicy）
    CONFLICT_POLICY = int(os.environ.get("CONFLICT_POLICY", "1"))
    # 视频文件扩展名（搬移分类用）
    VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".m4v", ".ts"}

    # 旧版单规则兼容（MOVER_RULES 为空时使用）
    MOVER_MONITOR_PATH = os.environ.get("MOV_MONITOR_PATH", "")
    MOVER_VIDEO_DEST_BASE = os.environ.get("MOV_VIDEO_DEST_BASE", "")
    MOVER_TRASH_DEST = os.environ.get("MOV_TRASH_DEST", "")
    MOVER_SMALL_FILE_SIZE = int(os.environ.get("MOV_SMALL_FILE_SIZE", str(100 * 1024 * 1024)))
    MOVER_TRASH_KEYWORDS = {"sample", "trailer", "preview", "thumb", "tmp", "temp"}
    MOVER_FOLDER_PREFIX = os.environ.get("MOV_FOLDER_PREFIX", "目录")
    MOVER_MAX_FILES_PER_FOLDER = int(os.environ.get("MOV_MAX_FILES_PER_FOLDER", "10000"))
    MOVER_CLEANUP_EMPTY_DIRS = os.environ.get("MOV_CLEANUP_EMPTY_DIRS", "true").lower() in ("1", "true", "yes")


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
    # Stash GraphQL 请求重试次数（仅传输层失败重试：断连/超时/HTTP 5xx/响应非 JSON；业务错误不重试）
    STASH_GRAPHQL_RETRY_COUNT = int(os.environ.get("STASH_GRAPHQL_RETRY_COUNT", "3"))
    # Stash GraphQL 请求重试间隔（秒）
    STASH_GRAPHQL_RETRY_DELAY = int(os.environ.get("STASH_GRAPHQL_RETRY_DELAY", "2"))

    # ── CD2 离线任务轮询 ─────────────────────────────────────────
    # 离线任务首次检查前等待（秒）
    CD2_OFFLINE_INITIAL_WAIT = int(os.environ.get("CD2_OFFLINE_INITIAL_WAIT", "30"))
    # 离线任务轮询间隔（秒）
    CD2_OFFLINE_CHECK_INTERVAL = int(os.environ.get("CD2_OFFLINE_CHECK_INTERVAL", "30"))
    # 离线任务轮询最大页数
    CD2_OFFLINE_CHECK_MAX_PAGES = int(os.environ.get("CD2_OFFLINE_CHECK_MAX_PAGES", "5"))

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
                "monitor_path": cls.MOVER_MONITOR_PATH or "/path/to/video-incoming",
                "video_dest_base": cls.MOVER_VIDEO_DEST_BASE or "/path/to/classified",
                "trash_dest": cls.MOVER_TRASH_DEST or "/path/to/trash",
                "folder_prefix": cls.MOVER_FOLDER_PREFIX,
                "max_files_per_folder": cls.MOVER_MAX_FILES_PER_FOLDER,
                "small_file_size": cls.MOVER_SMALL_FILE_SIZE,
                "trash_keywords": cls.MOVER_TRASH_KEYWORDS,
                "cleanup_empty_dirs": cls.MOVER_CLEANUP_EMPTY_DIRS,
            },
        ]
