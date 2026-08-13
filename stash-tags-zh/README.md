# stash-tags-zh

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

> [Stash 小工具集](https://github.com/tanlidoushen/my-stash-toolbox/tree/main) 系列之一：中文汉化标签层级分析 + 汉化补丁导入工具。
> 从 Stash GraphQL 拉取中文标签体系（父/子层级 + 描述），并可将整套中文标签作为汉化补丁导入到英文标签的 Stash 实例。

> ⚠️ **破坏性操作警告**
> `import_tags.py --apply` 会**覆盖目标 Stash 的标签属性（name/aliases/description）并修改父子层级，不可逆**。
> 执行前必须**先备份目标 Stash 数据库**（Stash 设置 → Metadata → Backup Database，或备份容器数据目录），
> 并先跑 `--dry-run` 查看完整影响报告。

---

## 数据文件

| 文件 | 内容 | 数量 |
|------|------|------|
| `parents.json` | 有下级标签的**中文上级标签**（含子标签列表，按子数降序） | 28 |
| `children.json` | 有上级标签的**中文下级标签**（含父标签列表，按父数降序） | 2785 |

---

## 用法

```bash
# 拉取数据分析（生成 parents.json / children.json）
python3 fetch_tags.py --url http://<stash>:9999/graphql

# 汉化补丁导入（预览，不写库）
python3 import_tags.py --url http://<stash>:9999/graphql --dry-run

# 汉化补丁导入（实际执行：覆盖 + 新建 + 挂层级，⚠️ 破坏性操作，会二次确认）
python3 import_tags.py --url http://<stash>:9999/graphql --apply
```

- 中文判定：标签名含 `\u4e00-\u9fff` 中文字符
- 拉取日期：2026-08-13（全量 3903 标签，中文 3586）

---

## 导入（汉化补丁）匹配逻辑

| 对方情况 | 动作 |
|----------|------|
| 同名且 aliases/description 完全一致 | 跳过 |
| 同名但别名/描述不一致 | 覆盖（补齐 aliases/description） |
| 我的英文别名 ∈ 对方 name/aliases | 覆盖（name→中文，英文原名并入 aliases） |
| 我的中文名 ∈ 对方 aliases（半汉化） | 覆盖（name→中文） |
| 无匹配 | 新建 |

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

---

> 本工具大部分使用 Vibe Coding 方式开发。
> 遵循 [MIT License](https://github.com/tanlidoushen/my-stash-toolbox/blob/main/LICENSE) 开源协议。
