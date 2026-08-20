# stash-webhook-scanner

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](../LICENSE)

---

> 通过 CloudDrive2 Webhook 实时触发 Stash 扫描、刮削、归类与搬运，并提供 Telegram Bot 管理界面。

---

## 功能

| 模块 | 说明 |
|------|------|
| 文件扫描 | 接收 CD2 文件变更 Webhook，防抖后触发 Stash `metadataScan` |
| 文件搬移 | 根据规则将监控目录中的文件分类搬移到目标目录（分卷、清理空目录） |
| 元数据刮削 | 自动检测 JAV / Non-JAV，指纹预查三源（javstash / stashdb / theporndb）判定类型，多源合并刮削 |
| 标记同步 | Non-JAV 场景刮削后自动双源同步标记（timestamp.trade + theporndb） |
| 图库同步 | 场景刮削后自动为演员从 stash-box 拉取图片建 Gallery |
| TG Bot | `/scrape` `/rescan` `/delete` `/code` 等命令；`/code 番号` 搜索影片详情与磁力链接（AVDB 源）、离线下载、进度监控 |

## 部署

```bash
docker build -t stash-webhook-scanner .
docker run -d --name stash-webhook-scanner \
  --network host \
  -e STASH_URL="http://<stash-server>:9999/graphql" \
  -e STASH_BASE_URL="http://<stash-proxy>:9997" \
  -e CD2_SERVER="<cd2-server>:19798" \
  -e CD2_TOKEN="<your-cd2-token>" \
  -e TG_BOT_TOKEN="<your-bot-token>" \
  -e TG_CHAT_ID="<chat-id>" \
  -e TG_OWNER_ID="<owner-user-id>" \
  stash-webhook-scanner
```

## 关键环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `STASH_URL` | `http://<stash-server>:9999/graphql` | Stash GraphQL 端点 |
| `STASH_APIKEY` | 空 | Stash API Key（开启认证时必填） |
| `STASH_BASE_URL` | `http://<stash-proxy>:9997` | Stash 前端地址（生成超链接） |
| `CD2_SERVER` | `<cd2-server>:19798` | CloudDrive2 gRPC 地址 |
| `CD2_TOKEN` | 空 | CD2 访问令牌 |
| `CD2_OFFLINE_FOLDER` | `/path/to/media` | 磁力离线下载默认目录 |
| `TG_BOT_TOKEN` / `TG_CHAT_ID` / `TG_OWNER_ID` | 空 | Telegram Bot 配置 |
| `AVDB_API_URL` / `AVDB_API_KEY` | 占位 | AVDB 磁力聚合 API（需自备服务与 Key） |
| `STASHBOX_PROXY` | `http://<proxy>:7890` | stash-box 外网访问代理 |

完整配置见 [config.py](config.py)，均可通过环境变量覆盖。
