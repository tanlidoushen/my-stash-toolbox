# stashdb-proxy-zh

[![Go](https://img.shields.io/badge/Go-1.26%2B-blue)](https://go.dev)
[![License](https://img.shields.io/badge/License-MIT-green)](../LICENSE)

---

> stashdb.org 反向代理增强：全界面汉化 + 本地 Stash 库联动（中文标签映射、场景匹配播放）+ 图片缓存。
> 基于 OpenResty/Go 反代方案，浏览器零插件、零配置。

---

## 功能

| 模块 | 说明 |
|------|------|
| 界面汉化 | 导航栏、场景/演员/工作室详情页、列表页排序与筛选控件、主页区块标题全中文 |
| 标签增强 | 场景页标签实时映射为本地 Stash 中文标签（别名 → 本地主名），本地不存在则红框标记 |
| 本地场景匹配 | 卡片与详情页显示"本地播放"图标（按 stashdb 场景 ID 匹配本地库），一键跳转播放 |
| 本地筛选 | 工具栏支持"隐藏本地已有 / 只看本地"过滤，找新片或回顾收藏都方便 |
| 图片缓存 | 列表缩略图 / 详情封面走磁盘缓存（30 天 TTL，10GB 上限），重复浏览零回源 |
| 原生控件保留 | 原站排序（7 种）/ 收藏筛选（演员/工作室）控件保留，切换即同步刷新列表 |

---

## 工作原理

```
浏览器 ──> stashdb-proxy (Go 反代 :8900)
              │  ① HTML 注入增强脚本（界面汉化/卡片渲染/标签与场景匹配）
              │  ② /images/ 磁盘缓存（缩略图 400px / 封面 1280px 各一份）
              │  ③ /api/resolve-tags    ──> 本地 Stash 标签全量索引（内存，60min 刷新）
              │  ④ /api/resolve-scenes  ──> 本地 Stash 场景 stash_id 索引（内存，60min 刷新）
              └──> stashdb.org（回源，携带登录 Cookie）
```

- 标签/场景匹配**由后端一次性全量拉取本地库建内存索引**，前端批量请求毫秒级返回，不逐条查询本地库
- 播放跳转地址、查询地址均可在 `config.json` 中独立配置

---

## 部署

### 1. 准备配置

```bash
cp config.example.json config.json
```

编辑 `config.json`：

| 配置项 | 说明 |
|--------|------|
| `site.cookie` | stashdb.org 登录 Cookie（浏览器 F12 复制 `stashbox=...` 值） |
| `localStash.graphql` | 本地 Stash GraphQL 地址，如 `http://192.168.1.10:9999/graphql` |
| `localStash.playerUrl` | "本地播放"跳转地址，如 `http://192.168.1.10:9997` |
| `localStash.refreshMinutes` | 标签/场景索引刷新周期（默认 60 分钟） |
| `faviconProxy` | （可选）favicon 回源代理，被墙时需要 |
| `imageCache.maxSizeGB / ttlDays` | 图片缓存容量与有效期（默认 10GB / 30 天） |

> 登录 Cookie 过期后需重新获取；`config.json` 含凭据，已加入 `.gitignore` 不会误提交。

### 2. 构建与启动

```bash
# 构建镜像（Go 1.26 + 前端脚本合并）
./build.sh
docker build -t stashdb-proxy:latest .
docker compose up -d
```

> 开发迭代期前端脚本改动后执行 `./build.sh && docker compose up -d --force-recreate` 即可生效。

### 3. 访问

打开 `http://<host>:8900` 即可使用，浏览器无需安装任何插件。

---

## 目录结构

```
stashdb-proxy-zh/
├── main.go               # Go 反代：HTML 注入 / 图片缓存 / 标签与场景索引 API
├── web/                  # 前端增强脚本（build.sh 合并为 enhanced.js 注入）
│   ├── config.js         # 站点配置（API Key 需自行填入）
│   ├── main.js           # 列表页接管：卡片网格 / 工具栏 / 分页
│   ├── card-renderer.js  # 场景卡片渲染
│   ├── hanhua.js         # 汉化映射 + 标签/场景匹配渲染
│   ├── sorter.js         # 排序与筛选（含本地筛选）
│   └── ...
├── Dockerfile
├── docker-compose.yml
├── config.example.json   # 配置模板（复制为 config.json 后填写）
└── build.sh              # 合并 web/*.js → enhanced.js（go:embed 嵌入）
```

---

> 界面文案由 AI 翻译生成，仅供学习交流参考。
> 遵循 [MIT License](../LICENSE) 开源协议。
