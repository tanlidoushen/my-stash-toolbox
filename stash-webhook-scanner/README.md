# Stash Webhook Scanner

专为网盘监控响应打造的工具。开启 CloudDrive2 文件变更通知的 Webhook 后，即可在文件新增或移动时**实时触发 Stash 扫描与刮削**，实现从入库到元数据完善的全自动化流程。

> [CloudDrive2](https://www.clouddrive2.com/) 是一款网盘挂载工具，其**文件变更通知**为会员功能，支持在文件发生变化时推送 Webhook。  
> 如果你还没有 CloudDrive2 会员，可以使用我的推荐码：**Hp5P95Hy** [→ 前往官网](https://www.clouddrive2.com/)

## 功能

- **实时响应** — 收到 Webhook 后自动触发 Stash 扫描，无需手动操作
- **防抖聚合** — 短时间内的多次变更合并处理，避免重复扫描
- **智能过滤** — 按文件后缀和路径关键词筛选，只处理目标影片文件
- **路径映射** — 自动将 CloudDrive 路径转换为 Stash Docker 的实际挂载路径
- **自动刮削** — 扫描完成后自动从 stash-box 刮削并补充演员、工作室、标签等元数据

## 环境要求

- Python 3.9+
- 一个运行中的 [Stash](https://stashapp.cc) 实例
- 一个 [CloudDrive2](https://www.clouddrive2.com/) 会员账号，并启用 Webhooks 功能

## 安装

```bash
git clone <your-repo-url>
cd stash-webhook-scanner
pip install -r requirements.txt
```

## 配置

所有配置通过环境变量或 `config.py` 中的 `Config` 类进行管理：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `STASH_URL` | `http://localhost:9999/graphql` | Stash GraphQL API 地址 |
| `FLASK_HOST` | `0.0.0.0` | Flask 监听地址 |
| `FLASK_PORT` | `9991` | Flask 监听端口 |
| `DEBOUNCE_WAIT` | `10` | 防抖等待时间（秒） |
| `ALLOWED_EXTENSIONS` | `{`.mkv`, `.mp4`, `.avi`, `.rmvb`}` | 允许触发扫描的文件后缀 |
| `ALLOWED_KEYWORDS` | `{`/CloudDrive/media`}` | Webhook 推送的路径中必须包含的关键词，用于过滤无关文件 |
| `PATH_PREFIX_MAP` | `(("/CloudDrive/media", "/CloudNAS/CloudDrive/media"),)` | CloudDrive 云端路径 → Stash Docker 实际挂载路径的前缀映射 |

## 使用方法

### 1. 启动服务

```bash
python app.py
```

或通过环境变量自定义：

```bash
export STASH_URL=http://192.168.1.100:9999/graphql
export FLASK_PORT=9991
export DEBOUNCE_WAIT=15
python app.py
```

### 2. 配置 CloudDrive2 Webhooks

在 CloudDrive2 的设置中启用Webhooks，将 Webhook URL 指向：

```
http://<your-server>:9991/file_notify
```



## 项目结构

```
stash-webhook-scanner/
├── app.py          # Flask Webhook 服务器
├── config.py       # 配置类
├── handler.py      # 事件防抖、批处理和流水线编排
├── scanner.py      # Stash GraphQL API 客户端（扫描、刮削、元数据更新）
└── requirements.txt
```

## 许可证

MIT
