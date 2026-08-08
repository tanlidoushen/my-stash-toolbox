# Docker 部署指南

## 构建镜像

```bash
docker build -t stash-webhook-scanner .
```

如需指定代理（构建时拉取依赖）：

```bash
docker build \
  --build-arg HTTP_PROXY=http://proxy:7890 \
  --build-arg HTTPS_PROXY=http://proxy:7890 \
  -t stash-webhook-scanner .
```

## 快速启动

### 方式一：docker run

```bash
docker run -d --name stash-webhook-scanner \
  --restart unless-stopped \
  -p 9991:9991 \
  -e STASH_URL=http://stash:9999/graphql \
  -e CD2_SERVER=cd2-server:19798 \
  -e CD2_TOKEN=your-cd2-token \
  -e TG_BOT_TOKEN=your-bot-token \
  -e TG_CHAT_ID=your-chat-id \
  stash-webhook-scanner
```

### 方式二：docker compose

```yaml
services:
  stash-webhook-scanner:
    image: stash-webhook-scanner:latest
    container_name: stash-webhook-scanner
    restart: unless-stopped
    ports:
      - "9991:9991"
    environment:
      # ── 必填 ──
      STASH_URL: "http://stash:9999/graphql"
      CD2_SERVER: "cd2-server:19798"
      CD2_TOKEN: "your-cd2-token"

      # ── 可选 ──
      TG_BOT_TOKEN: ""
      TG_CHAT_ID: ""
      TG_OWNER_ID: "0"
      DEBOUNCE_WAIT: "10"
      FLASK_PORT: "9991"
    networks:
      - stash_default
      - cd2_default

networks:
  stash_default:
    external: true
  cd2_default:
    external: true
```

## 环境变量速查

### 必填（不配无法运行）

| 变量 | 说明 |
|------|------|
| `STASH_URL` | Stash GraphQL API 地址，如 `http://stash:9999/graphql` |
| `CD2_SERVER` | CloudDrive2 gRPC 地址，如 `192.168.1.100:19798` |
| `CD2_TOKEN` | CloudDrive2 访问令牌 |

### 重要（建议按环境配置）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `STASH_APIKEY` | `""` | Stash API Key（如果开启了认证） |
| `PATH_PREFIX_MAP` | — | 路径映射，在 `config.py` 中修改 |
| `ALLOWED_EXTENSIONS` | `{".mkv",".mp4",...}` | 触发扫描的文件后缀 |
| `ALLOWED_KEYWORDS` | — | 路径过滤关键词 |
| `TG_BOT_TOKEN` | `""` | Telegram Bot Token（留空不启用 Bot） |
| `TG_CHAT_ID` | `""` | 通知目标 Chat ID |
| `TG_OWNER_ID` | `0` | 所有者 User ID |

### 调优（可选）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FLASK_HOST` | `0.0.0.0` | 监听地址 |
| `FLASK_PORT` | `9991` | 监听端口 |
| `DEBOUNCE_WAIT` | `10` | Webhook 防抖（秒） |
| `WS_ENABLED` | `true` | 是否启用 WebSocket 订阅 |
| `JAV_SCRAPE_RETRY_COUNT` | `3` | 刮削重试次数 |
| `DEBUG` | `false` | 调试日志开关 |

## 网络拓扑

```
CloudDrive2 ──→ stash-webhook-scanner:9991
                      │
                      ├──→ Stash:9999/graphql（扫描、刮削）
                      │
                      └──→ Telegram API（通知推送）
```

容器需要能访问：
- **Stash** GraphQL API（扫描和刮削）
- **CloudDrive2** gRPC 端口（文件操作）
- **Telegram API**（可选，通知用）

## 日志

```bash
docker logs -f stash-webhook-scanner
```

默认日志级别为 INFO，设置 `DEBUG=true` 可查看详细的文件变更通知日志。

## 健康检查

Webhook 服务默认监听 `0.0.0.0:9991`，收到 CloudDrive2 推送的 `POST /file_notify` 请求后触发处理。
