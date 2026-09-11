# stash-tags-zh

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

> 中文汉化标签层级分析 + 汉化补丁导入工具。
> 标签由 AI 翻译生成，仅供学习交流参考。

> ⚠️ **破坏性操作警告**
> `import_tags.py --apply` 会**覆盖目标 Stash 的标签属性（name/aliases/description）并修改父子层级，不可逆**。
> 执行前必须**先备份目标 Stash 数据库**（Stash 设置 → Metadata → Backup Database，或备份容器数据目录），
> 并先跑 `--dry-run` 查看完整影响报告。

---

## 数据文件

| 文件 | 内容 | 数量 |
|------|------|------|
| `tags-v2.json` | 中文汉化标签全量（含云端 `stash_id`，按名称排序） | 2941 |

> **v2 数据格式**：每个标签含 `name` / `aliases` / `description` / `stash_id`（stashdb 云端 uuid）。
> 来源：本地 Stash 全量标签，与云端标签**一一绑定**（每个云端标签唯一对应一个本地标签）后导出，
> 用于校验汉化结果、回填云端 id。
>
> v1 的层级分析数据（`parents.json` / `children.json`，不含 stash_id）已移除。

---

## 用法

```bash
# 拉取层级分析数据（v1 工具，生成 parents.json / children.json）
python3 fetch_tags.py --url http://<stash>:9999/graphql

# 汉化补丁导入（预览，不写库）
python3 import_tags.py --url http://<stash>:9999/graphql --dry-run

# 汉化补丁导入（实际执行：覆盖 + 新建 + 挂层级，⚠️ 破坏性操作，会二次确认）
python3 import_tags.py --url http://<stash>:9999/graphql --apply
```

- 中文判定：标签名含 `\u4e00-\u9fff` 中文字符
- v2 数据快照：2026-09-11（全量 4077 标签，含云端 stash_id 的 2941）
- v1 拉取日期：2026-08-13（全量 3903 标签，中文 3586）

---

## 导入（汉化补丁）匹配逻辑

| 对方情况 | 动作 | description 处理 |
|----------|------|------------------|
| 同名且 aliases/description 完全一致 | 跳过 | 不动 |
| 同名但别名/描述不一致 | 覆盖（补齐 aliases/description） | 本地有则覆盖；本地为空则**保留对方原描述** |
| 我的英文别名 ∈ 对方 name/aliases | 覆盖（name→中文，英文原名并入 aliases） | 同上 |
| 我的中文名 ∈ 对方 aliases（半汉化） | 覆盖（name→中文） | 同上 |
| 无匹配 | 新建 | 写入本地描述（为空则留空） |

**description 覆盖规则**：进入「覆盖」的标签，本地描述非空 → 用中文描述覆盖；本地描述为空 → **保留对方原描述**，不会清空。

执行顺序：覆盖/新建所有标签 → 按 children.json 挂父子层级。

---

## 顶级分类速览（parents.json 全部 28 个）

| 上级标签 | 子标签数 |
|----------|---------|
| 性行为 | 716 |
| 服装 | 307 |
| 主题 | 289 |
| 情趣用品 | 234 |
| 杂项 | 222 |
| 角色 | 178 |
| 收尾动作 | 120 |
| 群戏组合 | 89 |
| 拍摄地点 | 79 |
| 人物关系 | 76 |
| 体型 | 57 |
| 拍摄类型 | 49 |
| 生殖器 | 48 |
| 发色 | 40 |
| 情绪 | 38 |
| 表面 | 38 |
| 种族 | 36 |
| 胸部 | 28 |
| 年龄组 | 26 |
| 发型 | 25 |
| 面部 | 20 |
| 穿孔(分类) | 19 |
| 动机 | 15 |
| 肤色 | 14 |
| 性向分类 | 9 |
| 臀部 | 8 |
| 身高 | 7 |
| 纹身 | 6 |
