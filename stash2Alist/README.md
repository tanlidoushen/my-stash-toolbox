# stash2alist

[![License](https://img.shields.io/badge/License-MIT-green)](../LICENSE)

> 基于 **OpenResty (nginx + Lua)** 的 Stash 流媒体透明代理，支持 **Alist** 和 **CloudDrive2** 两种直链获取方式，可运行时切换。

---

## 架构

```
Browser ──→ OpenResty:8000
              ├── / → proxy_pass → Stash:9999
              │     ├── Host 透传（Stash 生成正确 URL）
              │     ├── 响应体改写（移除 crossorigin）
              │     └── WebSocket 支持
              │
              ├── /api/mode → 运行时切换直链模式
              │
              └── /scene/{id}/stream → Lua 业务逻辑
                    ├── 查询 Stash GraphQL（查文件路径）
                    ├── 读取当前模式（alist / clouddrive2）
                    │
                    ├── [alist 模式]
                    │     ├── Alist 路径映射
                    │     ├── 缓存检查
                    │     ├── 请求 Alist /d/{path}（跟 302）
                    │     └── 302 → CDN 直链播放
                    │
                    └── [cd2 模式]
                          ├── CloudDrive2 路径映射
                          ├── 构造 CloudDrive2 下载链接（无需请求）
                          └── 302 → CloudDrive2 下载链接播放
```

---

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `STASH_SERVER` | 否 | `http://127.0.0.1:9999` | Stash 服务器地址 |
| `ALIST_SERVER` | 否 | `http://127.0.0.1:5244` | Alist 服务器地址 |
| `CD2_SERVER` | 否 | `http://127.0.0.1:19798` | CloudDrive2 服务器地址 |
| `PATH_MAPPINGS` | 否 | `[]` | Alist 路径映射规则（JSON 数组） |
| `CD2_PATH_MAPPINGS` | 否 | `[]` | CloudDrive2 路径映射规则（JSON 数组） |
| `CACHE_TTL` | 否 | `3600` | Alist 直链缓存默认 TTL（秒） |
| `STASH_API_KEY` | 否 | `""` | Stash API 密钥（可选） |
| `DEFAULT_MODE` | 否 | `alist` | 默认直链模式：`alist` 或 `cd2` |

---

## 快速启动

```bash
cd stash2alist

# 按需编辑 docker-compose.yml 中的环境变量
docker compose up -d
```

---

## 路径映射配置

### Alist 映射 (PATH_MAPPINGS)

```yaml
PATH_MAPPINGS: >
  [
    {"local":"/local/mount/path","alist":"/alist/virtual/path"}
  ]
```

### CloudDrive2 映射 (CD2_PATH_MAPPINGS)

```yaml
CD2_PATH_MAPPINGS: >
  [
    {"local":"/local/mount/path","cd2":"/cd2/virtual/path"}
  ]
```

- `local`: Stash 中文件的本地路径前缀
- `alist` / `cd2`: 对应的虚拟路径前缀
- 规则按 `local` 长度降序匹配（最长前缀优先）

---

## 运行时切换模式

### 查看当前模式

```bash
curl http://localhost:9997/api/mode
# {"mode":"alist","default":"alist"}
```

### 切换到 CloudDrive2

```bash
curl -X POST http://localhost:9997/api/mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"cd2"}'
# {"mode":"cd2","message":"switched to cd2"}
```

### 切换回 Alist

```bash
curl -X POST http://localhost:9997/api/mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"alist"}'
# {"mode":"alist","message":"switched to alist"}
```

> 模式切换立即生效，无需重启容器。重启后恢复为 `DEFAULT_MODE`。

---

## CloudDrive2 下载链接格式

```
{CD2_BASE}/static/http/{CD2_BASE}/False/{URL_ENCODED_PATH}
```

CloudDrive2 下载链接是确定性的（格式固定），无需像 Alist 那样请求 `/d/` 获取 302，因此不需要缓存。

---

## 直链获取流程

1. 客户端请求 `/scene/{id}/stream`
2. OpenResty 读取当前模式（共享字典 / 默认值）
3. 通过内部 subrequest 查询 Stash GraphQL，获取文件路径
4. **Alist 模式**：
   - 根据 `PATH_MAPPINGS` 映射为 Alist 路径
   - 请求 Alist `/d/{path}` 获取 302 直链
   - 缓存直链并 302 重定向
5. **CloudDrive2 模式**：
   - 根据 `CD2_PATH_MAPPINGS` 映射为 CloudDrive2 路径
   - 直接构造 CloudDrive2 下载链接 URL
   - 302 重定向到 CloudDrive2 下载链接

## 降级策略

如果任一环节失败（Stash 无响应、路径无匹配等），自动降级为 `@stash_direct`——直接透传回 Stash。

---

## 许可证

[MIT](../LICENSE)

