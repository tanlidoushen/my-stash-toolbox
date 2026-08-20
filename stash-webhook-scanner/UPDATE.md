# stash-webhook-scanner 发布版更新指南

> 本文档说明如何将**运行版**（私有仓库 `tanlidoushen/stash-webhook-scanner`）的代码同步到**发布版**（本公开仓库 `tanlidoushen/my-stash-toolbox`）。
>
> 发布版是脱敏删减版：不含私有密钥、内网地址、个人路径，也不含部分插件。

---

## 仓库对应关系

| | 运行版（私有） | 发布版（公开，本目录） |
|---|---|---|
| 本地路径 | `git/repos/stash-webhook-scanner/app/` | `git/repos/my-stash-toolbox/stash-webhook-scanner/` |
| 用途 | 完整源码，硬编码密钥可直接提交 | 脱敏模板，配置一律环境变量注入 |
| plugins | 8 个文件全量 | 仅 `avdb_plugin.py` + `base.py` + `loader.py` + `__init__.py` |
| 磁力源 | AVDB + JavDB | 仅 AVDB（无 JavDB API 调用） |

---

## 更新步骤

### 1. 整体重建发布版目录

```bash
cd /opt/hermes-agent/git/repos
rm -rf my-stash-toolbox/stash-webhook-scanner
mkdir -p my-stash-toolbox/stash-webhook-scanner
cp -a stash-webhook-scanner/app/. my-stash-toolbox/stash-webhook-scanner/
cd my-stash-toolbox/stash-webhook-scanner
```

> ⚠️ 本环境**无 rsync**，用 `cp -a`。

### 2. 清理不发布的文件

```bash
# 运行产物 / 备份 / 调试残留
find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null
rm -rf backups data performer_gallery_cli .git
find . -name '*.py.bak' -delete
rm -f test_*.py
rm -f mover/handler.7z            # 旧代码备份（无引用）
rm -f fix_gallery_link.py debug_title.py clean_gallery.py   # 含私有路径的调试脚本
```

### 3. 删除不发布的插件（重要）

```bash
# JavDB API 调用文件（含硬编码 JAVDB_SECRET）
rm -f plugins/javdb_plugin.py
rm -f bot/magnet_sources/javdb_source.py

# 其余刮削插件（发布版 plugins 只保留 avdb_plugin.py）
rm -f plugins/avdanyuwiki_plugin.py plugins/javlibrary_plugin.py plugins/shiroutowiki_plugin.py
```

> ⚠️ **保留** `plugins/base.py` 和 `plugins/loader.py`——它们是框架（avdb_plugin 与 pipeline 的依赖），**不要删，不要内联改造**。
> ⚠️ `bot/javdb_search*.py`（/code 命令、磁力展示、离线下载框架）**保留**——它们不调 JavDB API，只走磁力源管理器，删掉 JavDB 磁力源后自动只剩 AVDB。

### 4. 脱敏（值替换，不做逻辑改造）

| 文件 | 替换规则 |
|---|---|
| `config.py` | 内网 IP → `<stash-server>`/`<stash-proxy>`/`<cd2-server>`/`<avdb-server>`/`<proxy>` 等占位符；私有路径 `/115/...` `/netdisk` `/mnt/HDD_*` → `/path/to/...`；`MAGNET_AUTO_PICK_PREFER` 默认改 `"AVDB"` |
| `plugins/avdb_plugin.py` | 硬编码的 `AVDB_API_URL`（内网 IP）与 `AVDB_API_KEY`（真实 Key）→ `os.environ.get(...)` 占位 |
| `Dockerfile` | 删除私有代理 ENV（HTTP_PROXY/NO_PROXY 内网地址） |
| `scrape/box.py`、`scrape/marker_sync.py`、`scrape/performer_gallery.py` | 兜底默认值 `STASHBOX_PROXY`/`PERFORMER_GALLERY_PATH`/flaresolverr URL → 占位符 |
| `stash/delete.py` | 注释中的私有路径泛化 |

> 替换注意：`欧美影片目录` 含 `影片目录` 子串，**先替换长的**。
> 脱敏后全仓扫描确认零残留：`grep -rn -E "192\.168\.|jdforrepam|/115/|/netdisk|/mnt/HDD|/vol1" --include="*.py" .`

### 5. 验证

```bash
# 语法
python3 -m py_compile config.py plugins/*.py scrape/*.py bot/*.py

# 容器内 import 验证（docker run -v 挂 Hermes 路径无效，用 docker cp）
docker exec stash-webhook-scanner sh -c "rm -rf /tmp/pubtest && mkdir -p /tmp/pubtest"
docker cp . stash-webhook-scanner:/tmp/pubtest/
docker exec stash-webhook-scanner python3 -c "
import sys; sys.path.insert(0, '/tmp/pubtest')
from plugins.avdb_plugin import AvdbPlugin          # 插件加载正常
from scrape.pipeline import PluginLoader            # 框架依赖正常
from bot.magnet_sources import get_magnet_manager
print([(s.name, s.priority) for s in get_magnet_manager().sources])  # 期望只剩 [('AVDB', 100)]
"
docker exec stash-webhook-scanner rm -rf /tmp/pubtest
```

### 6. 提交推送

```bash
cd /opt/hermes-agent/git/repos/my-stash-toolbox
git add stash-webhook-scanner/
git commit -m "stash-webhook-scanner: 同步最新源码 + 脱敏"
https_proxy=<proxy> git push origin main
```

> ⚠️ **不要改写 git 历史**（不要 reset / force push）——正常提交删除即可，历史保持原样。

---

## 更新后自检清单

- [ ] `plugins/` 只有 `avdb_plugin.py` / `base.py` / `loader.py` / `__init__.py`
- [ ] 无 `jdforrepam` / `JAVDB_SECRET` / 内网 IP / 私有路径残留
- [ ] 容器 import 全过，磁力源只剩 AVDB
- [ ] 逻辑代码与运行版一致（`diff -rq` 仅脱敏文件有差异）
