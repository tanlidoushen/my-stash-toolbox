# stash-tags-zh

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

> 中文汉化标签工具：拉取（v2 含云端 stash_id）+ 汉化补丁导入。
> 标签由 AI 翻译生成，仅供学习交流参考。

> ⚠️ **破坏性操作警告**
> `import_tags.py --apply` 会覆盖目标 Stash 的标签属性（name/aliases/description）并回填 stash_id，**不可逆**。
> 执行前必须**先备份目标 Stash 数据库**（Stash 设置 → Metadata → Backup Database，或备份容器数据目录），
> 并先跑 `--dry-run` 查看完整影响报告。

---

## 数据文件

| 文件 | 内容 | 数量 |
|------|------|------|
| `tags-v2.json` | 中文汉化标签全量（含云端 `stash_id`，按名称排序） | 2941 |

> **v2 数据格式**：每个标签含 `name` / `aliases` / `description` / `stash_id`（stashdb 云端 uuid）。
> 来源：本地 Stash 全量标签，与云端标签**一一绑定**（每个云端标签唯一对应一个本地标签）后导出，
> 用于汉化补丁导入、校验与回填云端 id。
>
> v1 的层级分析数据（`parents.json` / `children.json`，不含 stash_id）已移除。

---

## 用法

```bash
# 拉取 v2 数据（生成 tags-v2.json，默认只导出有 stash_id 的标签）
python3 fetch_tags.py --url http://<stash>:9999/graphql

# 导出全部标签（含无 stash_id 的）
python3 fetch_tags.py --url http://<stash>:9999/graphql --all

# 汉化补丁导入（预览，不写库）
python3 import_tags.py --url http://<stash>:9999/graphql --dry-run

# 汉化补丁导入（实际执行：覆盖 + 新建 + 回填 stash_id，⚠️ 破坏性操作，会二次确认）
python3 import_tags.py --url http://<stash>:9999/graphql --apply
```

- v2 数据快照：2026-09-11（全量 4077 标签，含云端 stash_id 的 2941）

---

## 导入（汉化补丁）匹配逻辑

匹配优先级（按序）：

| 优先级 | 匹配方式 | 动作 |
|--------|----------|------|
| 1 | **stash_id 精确匹配**（云端 id 唯一，最可靠） | 覆盖 |
| 2 | 同名匹配 | 覆盖 |
| 3 | 本地英文别名命中对方 name/aliases | 覆盖（英文原名并入 aliases） |
| 4 | 无匹配 | 新建（写入 stash_id） |

**覆盖内容**：name（汉化）/ aliases（合并去重）/ description（本地为空则**保留对方原描述**）/ stash_id（目标无则回填）。

**注意**：v2 数据不含父子层级，导入不执行层级挂载。

执行顺序：覆盖/新建所有标签，最后回填/校验 stash_id。
