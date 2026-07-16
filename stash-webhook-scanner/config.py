import os


class Config:
    # Stash GraphQL API 地址
    STASH_URL = os.environ.get("STASH_URL", "http://localhost:9999/graphql")

    # Flask 监听配置
    FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.environ.get("FLASK_PORT", "9991"))

    # 防抖等待时间（秒）
    DEBOUNCE_WAIT = int(os.environ.get("DEBOUNCE_WAIT", "10"))

    # 允许触发扫描的文件后缀
    ALLOWED_EXTENSIONS = {".mkv", ".mp4", ".avi", ".rmvb"}

    # Webhook 推送的路径中必须包含的关键词，用于过滤无关文件
    ALLOWED_KEYWORDS = {"/CloudDrive/media"}

    # CloudDrive 云端路径 → Stash Docker 实际挂载路径的前缀映射
    PATH_PREFIX_MAP = (
        ("/CloudDrive/media", "/CloudNAS/CloudDrive/media"),
    )
