# stash-tag-manager

Stash 标签分类整理工作区（孤儿标签 → 父层级归类）。

## 目录结构

```
stash-tag-manager/
├── data/            # 原始数据（Stash 全量标签 / 孤儿标签导出）
│   ├── all_tags.json / .txt
│   └── orphan_tags.json / .txt
├── docs/            # 归类方案设计文档
│   ├── 归类方案设计.md              (v1)
│   └── 归类方案设计_v2_大模型版.md  (v2, 大模型辅助)
├── results/         # 当前有效归类结果
│   └── 归类结果_v2/
│       ├── 归类结果_v2.json        (完整匹配结果)
│       ├── 归类结果_v2.md          (可读报告, 按父类分组)
│       ├── 归类结果_v2_raw.json    (LLM 原始输出)
│       └── 未归类_待确认.json      (待人工确认)
└── archive/         # 历史归档
    └── 旧归类结果/  (v1 归类结果, 保留备查)
```

## 归档说明

- 2026-08-13 整理：按 data / docs / results / archive 分类归档
- v1 归类结果移入 `archive/旧归类结果/`（内容已被 v2 取代，仅保留备查）
- 目录内不含运行代码；分类流程见 stash-tag-management 技能
