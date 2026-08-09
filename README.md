# Stash 小工具集

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

> 围绕 Stash 的一系列实用工具，覆盖自动刮削、流媒体代理、字幕下载等场景。

---

## 工具列表

| 工具 | 说明 |
|------|------|
| [stash-webhook-scanner](stash-webhook-scanner/) | 通过 CloudDrive2 Webhook 实时触发 Stash 扫描、刮削、归类与搬运 |
| [stash2Alist](stash2Alist/) | 基于 OpenResty 的 Stash 流媒体透明代理，支持 Alist / CloudDrive2 双模式 |
| [stash-graphql-skill](stash-graphql-skill/) | Stash GraphQL API 参考文档，覆盖 Query/Mutation/Subscription 全量字段与常用操作示例 |
| [plugins/StashSubtitleAssistant](plugins/StashSubtitleAssistant/) | Stash 插件：检索并下载字幕至视频目录，自动触发扫描 |

---

## 鸣谢

- 感谢 [ag123gfa12/JAV-JHS](https://github.com/ag123gfa12/JAV-JHS) 字幕 API 调用及脚本样式参考
- 感谢 [hippochapel/hippo-stash-plugins](https://github.com/hippochapel/hippo-stash-plugins) 的按键注入与面板实现参考
- 感谢 [bpking1/embyExternalUrl](https://github.com/bpking1/embyExternalUrl) 的 htmlvideoplayer 跨域实现参考

## 推荐项目

- [feldorn/Stash-Jellyfin-Proxy](https://github.com/feldorn/Stash-Jellyfin-Proxy) — Jellyfin API 模拟代理，让 Infuse、Yamby 等播放器直接浏览 Stash 媒体库

---

> 本工具大部分使用 Vibe Coding 方式开发。
> 遵循 [MIT License](LICENSE) 开源协议。


