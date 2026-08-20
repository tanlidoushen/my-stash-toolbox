"""刮削数据源配置（2026-08-17）：一个模块，两个应用。

JAV / Non-JAV 各自是一个"源列表"（ScrapeSource 列表），统一由 scrape/box.py 调度。
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScrapeSource:
    name: str                       # 'stashdb' / 'theporndb' / 'javstash'
    endpoint: str                   # GraphQL endpoint
    role: str = "fallback"          # 'primary'（第一数据源，单值字段优先）/ 'fallback'（补充）
    fingerprint_supported: bool = True  # 支持 findScenesBySceneFingerprints
    domain: str = ""                # performer URL 交叉引用判断用（如 'stashdb.org'）


NONJAV_SOURCES = [
    ScrapeSource(
        name="stashdb",
        endpoint="https://stashdb.org/graphql",
        role="primary",
        fingerprint_supported=True,
        domain="stashdb.org",
    ),
    ScrapeSource(
        name="theporndb",
        endpoint="https://theporndb.net/graphql",
        role="fallback",
        fingerprint_supported=True,
        domain="theporndb.net",
    ),
]

# JAV 应用（javstash 指纹支持已验证 2026-08-19：findScenesBySceneFingerprints 可用）
JAV_SOURCES = [
    ScrapeSource(
        name="javstash",
        endpoint="https://javstash.org/graphql",
        role="primary",
        fingerprint_supported=True,
        domain="javstash.org",
    ),
]

# JAV 交叉引用源（用于从 javstash 场景/演员 URL 中提取 stashdb ID 补抓数据）
# 2026-08-19 起 javstash 支持指纹，JAV 判定优先级：指纹预查 javstash → stashdb/tpdb → 文件名回退
JAV_CROSSREF_SOURCES = [
    ScrapeSource(
        name="javstash",
        endpoint="https://javstash.org/graphql",
        role="primary",
        fingerprint_supported=True,
        domain="javstash.org",
    ),
    ScrapeSource(
        name="stashdb",
        endpoint="https://stashdb.org/graphql",
        role="fallback",
        fingerprint_supported=True,
        domain="stashdb.org",
    ),
    ScrapeSource(
        name="theporndb",
        endpoint="https://theporndb.net/graphql",
        role="fallback",
        fingerprint_supported=True,
        domain="theporndb.net",
    ),
]

# 全局：所有参与指纹查库的源（合并 NONJAV + JAV 中支持的）
FINGERPRINT_SOURCES = tuple(
    s for s in (NONJAV_SOURCES + JAV_SOURCES) if s.fingerprint_supported
)


def get_source_by_name(name: str) -> ScrapeSource | None:
    for s in NONJAV_SOURCES + JAV_SOURCES:
        if s.name == name:
            return s
    return None


def get_primary(source_list) -> ScrapeSource | None:
    for s in source_list:
        if s.role == "primary":
            return s
    return source_list[0] if source_list else None