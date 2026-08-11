# 磁力搜索流水线（{STASH_CONTAINER}，多来源 → CD2 离线下载）

2026-08 实测记录：`/code 番号` 磁力搜索 = JavDB 影片/磁力 + AVDB 聚合磁力源，合并后走统一展示/下载/监控链路。

## 统一磁力 dict（下游展示/下载不区分来源）

| 字段 | 说明 |
|---|---|
| `hash` | btih 哈希（大写归一） |
| `url` | 完整 magnet（含 `&dn=`，可选；AVDB 有，JavDB 无） |
| `name` | 标题；展示截断 50 字符（`[:47]+"..."`） |
| `size` | 大小（MB）；0 → 显示"未知" |
| `cnsub` / `hd` | 中字 / 高清徽标 |
| `source` | 站点名，**原样完整显示**（含 emoji，如 `🌸色花堂🍑中文字幕`；用户明确要求不去 emoji 不截断） |
| `number` | 可多番号逗号分隔（`JUR-769,JUR-00769`），仅展示不参与匹配 |
| `preview_image` | 封面兜底图 |

## AVDB 聚合 API（bot/avdb_api.py）

- `GET http://{CD2_HOST}:{AVDB_API_PORT}/api/v1/articles/torrents?keyword=<番号>`，Header `X-API-Key`
- 成功判定 **`code == 0`**（≠ JavDB 的 `success == 1`）
- 字段映射：`download_url`→`hash`（正则 `btih:([0-9a-fA-F]{40})`）+`url`、`title`→`name`、`size_mb`→`size`、`chinese`→`cnsub`、`hd`→`hd`、`site`→`source`、`preview_image` 保留；`seeders` 不展示
- 无效条目（非 magnet / 无 btih）丢弃；失败/超时/`code!=0` → 记 warning 返回 `[]`，**绝不影响 JavDB 主流程**

## 合并、排序、去重

- `merge_magnets(javdb, avdb)`：按 btih 小写去重，**AVDB 优先保留**；无 hash 条目原样保留
- `_format_magnets` 排序键 `(0 if source else 1, 0 if cnsub else 1 if hd else 2, -size)`：AVDB（带 source）整体置顶；**纯 JavDB 时与旧"中字→高清→其他按大小"分组拼接排序完全一致**（无回归，验证过）
- 展示尾注 `🖥<source>`；按钮/分页/添加离线链路复用原 `_magnet_cache`（movie_id → 合并后列表）

## 封面兜底

`handle_javdb_detail._fetch()` 用 `asyncio.gather` 并行拉两源磁力；`avdb_cover` = AVDB 结果第一条非空 `preview_image`。发送封面 `_try_send_cover([javdb_cover, avdb_cover])` 依次尝试，都失败回退纯文本。`_download_cover` 按 UA 列表重试（`Dart/3.5 (dart:io)` → 浏览器 UA）——AVDB 图片域名可能不认 Dart UA。

## 下载

`magnet_url = magnet.get("url") or ("magnet:?xt=urn:btih:%s" % hash)`——url 优先（保留 `&dn=`，离线任务显示名更准），JavDB 磁力无 url 走 hash 拼接。

## 配置（config.py）

```python
AVDB_API_ENABLED = ...  # 默认开启（"" 计入 true）；失败自动降级无害
AVDB_API_URL = os.environ.get("AVDB_API_URL", "http://{CD2_HOST}:{AVDB_API_PORT}/api/v1/articles/torrents")
AVDB_API_KEY = os.environ.get("AVDB_API_KEY", "")
AVDB_API_TIMEOUT = int(os.environ.get("AVDB_API_TIMEOUT", "10"))
```

## 本地验证模式（无 Telegram 环境）

磁力/回调 handler 用假对象直接驱动：
- `FakeQuery`：`answer`、`edit_message_text`（记录文本）、`message.chat_id/message_id`、`bot`
- `FakeBot`：`send_message`（返回带 `message_id` 的对象）、`edit_message_reply_markup`、`delete_message`
- handler 内 `from stash.cd2_offline import add_offline_download` 是**调用时导入** → monkeypatch `stash.cd2_offline.add_offline_download` 即可拦截
- 测完手动 cancel `_monitor_tasks` 中新建任务（跨用例隔离）
- 运行：NAS 上 `docker exec {STASH_CONTAINER} python <脚本>`（容器 python:3.12-slim = 生产运行环境；Windows 时代 `env -u PYTHONPATH {PYTHON_EXE_PATH}` 已随 2026-08-07 迁移失效）
