# stash2Alist

> **Stash** 流媒体播放请求透明劫持 → 重定向到 **Alist** 直链，实现在线播放不走 Stash 服务器带宽。

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---



## 快速开始 / Quick Start

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 修改配置

编辑 `config.yaml`：

```yaml
stash:
  url: "http://192.168.1.100:9999"   # 你的 Stash 地址

alist:
  url: "http://192.168.1.100:5244"   # 你的 Alist 地址

path_mappings:
  - local: "/mnt/alist115"    # rclone 挂载路径
    alist: "/115"             # Alist 中对应的存储路径

```


### 3. 启动

```bash
# 使用默认配置 (config.yaml)
python -m stash2Alist

# 指定配置路径
python -m stash2Alist --config /path/to/config.yaml

# 覆盖监听地址
python -m stash2Alist --host 0.0.0.0 --port 8000

# 详细日志 / 调试模式
python -m stash2Alist -v
python -m stash2Alist --debug
```



---

## 项目结构 / Project Structure

```
stash2Alist/
├── __init__.py         # 包版本信息
├── __main__.py         # CLI 入口
├── app.py              # Starlette 应用 + 路由 + 透明代理
├── config.yaml         # 配置文件
├── requirements.txt    # Python 依赖
├── cache.py            # TTL 缓存（异步安全）
├── path_mapper.py      # 路径前缀映射
├── stash/
│   ├── __init__.py
│   └── client.py       # Stash GraphQL 客户端
└── alist/
    ├── __init__.py
    └── client.py       # Alist 直链获取（拼接 /d/{path} + 跟 302）
```

---

## 配置参考 / Configuration

### 环境变量

| 变量名 | 作用 |
|--------|------|
| `STASH2ALIST_CONFIG` | 指定配置文件路径（替代 `--config` 参数） |

### CLI 参数

| 参数 | 说明 |
|------|------|
| `--config PATH` | 配置文件路径（默认: `config.yaml`） |
| `--host HOST` | 监听地址（覆盖配置） |
| `--port PORT` | 监听端口（覆盖配置） |
| `--debug` | 调试模式，打印每个请求的详细信息 |
| `-v / --verbose` | 详细日志输出 |

### 信息接口

启动后访问 `http://host:8000/info` 可查看当前配置摘要。

---

## 依赖 / Dependencies

- [Starlette](https://www.starlette.io/) — Web 框架
- [Uvicorn](https://www.uvicorn.org/) — ASGI 服务器
- [httpx](https://www.python-httpx.org/) — HTTP 客户端（异步）
- [PyYAML](https://pyyaml.org/) — YAML 解析
- [websockets](https://websockets.readthedocs.io/) — WebSocket 代理

---

## License

[MIT](LICENSE)
