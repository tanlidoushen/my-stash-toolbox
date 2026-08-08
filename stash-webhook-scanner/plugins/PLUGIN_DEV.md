# Plugin 开发指南

插件系统通过 `plugins/loader.py` 自动发现和加载 `plugins/` 目录下所有 `*_plugin.py` 文件（排除 `base.py`、`loader.py`、`__init__.py`）。

## 快速开始

在 `plugins/` 目录下新建一个 `*_plugin.py` 文件，继承 `BasePlugin` 并实现 `scrape` 方法即可自动生效：

```python
"""示例插件 — 从目标网站抓取中文标题和演员。"""
import logging
import httpx
from plugins.base import BasePlugin

logger = logging.getLogger(__name__)


class MyPlugin(BasePlugin):

    @property
    def name(self) -> str:
        return "myplugin"

    async def scrape(self, japanese_code: str, scene_info: dict = None) -> dict:
        """抓取番号 japanese_code 的补充元数据。

        参数:
            japanese_code: 归一化的番号（如 START-273）。
            scene_info:    当前 Stash 场景已有数据（兜底判断用），
                           有值表示 stash-box 已命中，插件只需补充；
                           为 None 表示 stash-box 未命中，插件可作全量兜底。

        返回:
            dict，支持的键：
            - title:       str           覆盖标题（仅非日文时使用）
            - details:     str           覆盖简介
            - performers:  list[dict]    追加演员，每项: {"name": str, "gender": "FEMALE"|"MALE"}
            - tags:        list[dict]    追加标签，每项: {"name": str}
            - urls:        list[str]     追加 URL
        """
        logger.info("         - [Plugin:myplugin] 搜索 %s", japanese_code)

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"https://example-api.com/search?q={japanese_code}")
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning("         - [Plugin:myplugin] 请求失败: %s", e)
            return {}

        if not data:
            return {}

        return {
            "title": data.get("title"),
            "performers": [{"name": p} for p in data.get("actors", [])],
            "urls": [f"https://example.com/movie/{data['id']}"],
        }
```

## 插件加载规则

- 文件名必须以 `_plugin.py` 结尾（如 `myplugin_plugin.py`）
- 文件中必须有一个继承 `BasePlugin` 的类
- 插件在首次使用时被加载并缓存（文件系统只扫描一次）
- 加载失败仅记日志，不影响其他插件和主流程

## scrape 方法返回值

`merge_plugin_into_scraped()` 函数处理插件返回的数据，支持的字段：

| 字段 | 类型 | 行为 |
|------|------|------|
| `title` | `str` | 覆盖 stash-box 刮削的标题 |
| `details` | `str` | 覆盖简介 |
| `performers` | `list[dict]` | 按 `name` 去重后追加演员 |
| `tags` | `list[dict]` | 按 `name` 去重后追加标签 |
| `urls` | `list[str]` | 去重后追加 URL |

### performers 条目格式

```python
{"name": "演员名", "gender": "FEMALE"}   # FEMALE 或 MALE（可选）
```

### tags 条目格式

```python
{"name": "标签名"}
```

## 完整示例

一个完整的插件通常包含：

1. **API 客户端**（可选）— 封装对目标网站的 HTTP 请求
2. **字段提取器**（可选）— 从响应中提取标题、演员、标签
3. **Plugin 类** — 继承 `BasePlugin`，在 `scrape()` 中编排以上逻辑

参考 `plugins/loader.py` 的 `PluginLoader.discover()` 了解加载细节。

