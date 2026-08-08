# stash-webhook-scanner

> **CloudDrive2** 文件变更通知 Webhook 实时触发 **Stash** 扫描、刮削、归类与搬运，实现从入库到元数据完善的全自动化流程。

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](../LICENSE)

> [CloudDrive2](https://www.clouddrive2.com/) 是一款网盘挂载工具，其**文件变更通知**为会员功能，支持在文件发生变化时推送 Webhook。  
> 如果你还没有 CloudDrive2 会员，下单时使用推荐码 **Hp5P95Hy** 可享优惠：
> 月度会员及年度会员 **优惠10%**，终身会员 **优惠20%**

---

## 功能 / Features

- **实时响应** — 收到 Webhook 后自动触发 Stash 扫描，无需手动操作
- **防抖聚合** — 短时间内的多次变更合并处理，避免重复扫描
- **按需过滤** — 按文件后缀和路径关键词筛选，只处理目标影片文件
- **路径映射** — 自动将 CloudDrive 路径转换为 Stash 的实际挂载路径
- **自动刮削** — 扫描完成后自动从 stash-box 刮削并补充元数据
- **JAV/Non-JAV 智能识别** — 根据目录规则和文件名检测自动区分影片类型
- **可插拔刮削引擎** — 插件式架构，支持自定义刮削源
- **文件归类搬运** — 自动将文件按规则归类到指定目录，支持分卷管理
- **CloudDrive2 gRPC 集成** — 直接通过 CloudDrive2 gRPC API 操作文件（删除、搬移）
- **Telegram Bot** — 完整的 TG 机器人管理界面，支持：
  - `/scrape` — 按场景 ID 触发刮削（可选指定 JAV / Non-JAV）
  - `/rescan` — 快速重新刮削，跳过已有元数据
  - `/delete` — 按场景 ID 或番号删除，从 CD2 物理删除文件 + Stash 移除记录
  - `/archive_task` — 手动触发文件归类搬运
  - `/mode` — 查看/切换 stash2alist 代理模式（Alist / CloudDrive2）
  - `/start` — 内联键盘主菜单，所有功能可视化导航
  - **自动通知** — 刮削/归类完成后自动推送结果（含海报预览）
- **WebSocket 订阅** — 实时监听 Stash 扫描/刮削任务状态

---

## 项目结构 / Project Structure

```text
stash-webhook-scanner/
├── app.py                      # Flask Webhook 入口服务
├── config.py                   # 统一配置类（所有配置通过环境变量覆盖）
├── Dockerfile                  # Docker 镜像构建文件
├── DOCKER.md                   # Docker 部署指南
├── requirements.txt            # Python 依赖
├── cd2_client.py               # CloudDrive2 gRPC 客户端
├── clouddrive.proto            # CloudDrive2 gRPC protobuf 定义
├── server/                     # Webhook 服务器逻辑
│   ├── handler.py              #   事件防抖和批处理
│   └── dedup.py                #   去重处理
├── scrape/                     # 刮削流水线
│   ├── pipeline.py             #   刮削编排
│   ├── detector.py             #   JAV/Non-JAV 检测
│   ├── stashbox.py             #   Stash-box 刮削
│   ├── enrich.py               #   元数据补充
│   ├── merge.py                #   元数据合并
│   └── code.py                 #   番号提取
├── stash/                      # Stash GraphQL API 客户端
│   ├── client.py               #   基础客户端
│   ├── scanner.py              #   扫描操作
│   ├── scene.py                #   场景操作
│   ├── performer.py            #   演员操作
│   ├── studio.py               #   工作室操作
│   ├── tag.py                  #   标签操作
│   ├── query.py                #   查询工具
│   ├── delete.py               #   删除操作
│   └── ws_subscriber.py        #   WebSocket 实时订阅
├── mover/                      # 文件归类搬运
│   ├── mover.py                #   搬移引擎
│   ├── handler.py              #   事件处理
├── bot/                        # Telegram Bot
│   ├── app.py                  #   Bot 入口
│   ├── handlers.py             #   消息处理器
│   ├── callbacks.py            #   回调处理
│   └── utils.py                #   通用工具
├── plugins/                    # 刮削插件（自动发现）
│   ├── base.py                 #   插件基类
│   ├── loader.py               #   插件加载器
│   └── PLUGIN_DEV.md           #   插件开发指南
├── notify/                     # 通知系统
│   ├── telegram.py             #   Telegram 通知发送
│   └── builder.py              #   消息构建
└── __init__.py
```

---

## 快速开始 / Quick Start

### 使用 Docker（推荐）

详细部署指南见 [DOCKER.md](DOCKER.md)，包含镜像构建、环境变量说明、docker-compose 示例和网络拓扑。

快速启动：

```bash
docker build -t stash-webhook-scanner .
docker run -d --name stash-webhook-scanner -p 9991:9991 \
  -e STASH_URL=http://your-stash:9999/graphql \
  stash-webhook-scanner
```

### 直接运行

```bash
pip install -r requirements.txt
python app.py
```

所有配置通过环境变量覆盖，详见 `config.py`。

---

## 环境变量 / Environment Variables

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `STASH_URL` | `http://localhost:9999/graphql` | Stash GraphQL API 地址 |
| `FLASK_PORT` | `9991` | Flask 监听端口 |
| `DEBOUNCE_WAIT` | `10` | 防抖等待时间（秒） |
| `CD2_SERVER` | — | CloudDrive2 gRPC 地址 |
| `CD2_TOKEN` | — | CloudDrive2 访问令牌 |
| `TG_BOT_TOKEN` | — | Telegram Bot Token |
| `TG_CHAT_ID` | — | 通知目标 Chat ID |
| 更多配置项 | — | 见 `config.py` |

---

## 许可证 / License

[MIT](../LICENSE)


