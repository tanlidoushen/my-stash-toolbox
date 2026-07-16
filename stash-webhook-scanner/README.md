# stash-webhook-scanner

> **CloudDrive2** 文件变更通知 Webhook 实时触发 **Stash** 扫描与刮削，实现从入库到元数据完善的全自动化流程。

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-lightgrey)](https://flask.palletsprojects.com)

---

> [CloudDrive2](https://www.clouddrive2.com/) 是一款网盘挂载工具，其**文件变更通知**为会员功能，支持在文件发生变化时推送 Webhook。  
> 如果你还没有 CloudDrive2 会员，可以使用我的推荐码：**Hp5P95Hy** [→ 前往官网](https://www.clouddrive2.com/)

---

## 功能 / Features

* **实时响应** — 收到 Webhook 后自动触发 Stash 扫描，无需手动操作。
* **防抖聚合** — 短时间内的多次变更合并处理，避免重复扫描。
* **按需过滤** — 按文件后缀和路径关键词筛选，只处理目标影片文件。
* **路径映射** — 自动将 CloudDrive 路径转换为 Stash 的实际挂载路径。
* **自动刮削** — 扫描完成后自动从 stash-box 刮削并补充演员、工作室、标签等元数据。

---

## 环境要求 / Requirements

* Python 3.9+
* 一个运行中的 [Stash](https://stashapp.cc) 实例
* 一个运行中的 [CloudDrive2](https://www.clouddrive2.com/) 实例（需开通会员并启用 Webhooks 功能）

---

## 快速开始 / Quick Start

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 修改配置

所有配置通过环境变量或 `config.py` 中的 `Config` 类进行管理。你可以直接修改代码中的默认值，或者在启动服务时通过环境变量进行覆盖。

| 环境变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `STASH_URL` | `http://localhost:9999/graphql` | Stash GraphQL API 地址 |
| `FLASK_HOST` | `0.0.0.0` | Flask 监听地址 |
| `FLASK_PORT` | `9991` | Flask 监听端口 |
| `DEBOUNCE_WAIT` | `10` | 防抖等待时间（秒） |
| `ALLOWED_EXTENSIONS` | `{".mkv", ".mp4", ".avi", ".rmvb"}` | 允许触发扫描的文件后缀 |
| `ALLOWED_KEYWORDS` | `{"/CloudDrive/media"}` | Webhook 推送的路径中必须包含的关键词（用于过滤无关文件） |
| `PATH_PREFIX_MAP` | `(("/CloudDrive/media", "/CloudNAS/CloudDrive/media"),)` | CloudDrive 云端路径 → Stash Docker 实际挂载路径的前缀映射 |

### 3. 启动服务

使用默认配置启动：

```bash
python app.py
```

或者通过环境变量自定义参数启动：

```bash
export STASH_URL=[http://192.168.1.100:9999/graphql](http://192.168.1.100:9999/graphql)
export FLASK_PORT=9991
export DEBOUNCE_WAIT=15
python app.py
```

---

## Webhook 配置 / Webhook Configuration

### 配置 CloudDrive2 Webhooks

在 CloudDrive2 的设置中启用 Webhooks，将 Webhook URL 指向：

```text
http://<your-server>:9991/file_notify
```

---

## 项目结构 / Project Structure

```text
stash-webhook-scanner/
├── app.py              # Flask Webhook 服务器
├── config.py           # 配置类
├── handler.py          # 事件防抖、批处理和流水线编排
├── scanner.py          # Stash GraphQL API 客户端（扫描、刮削、元数据更新）
└── requirements.txt    # Python 依赖
```

---

## 许可证 / License

[MIT](LICENSE)