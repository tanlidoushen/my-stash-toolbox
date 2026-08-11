# grpcurl → grpcio 迁移（{STASH_CONTAINER}）

**状态：✅ 已实施（2026-08-05）**。本文先记为什么迁移，再记实际落地形态与实测结果。

## 为什么迁移

旧 `mover/cd2_client.py` 的 `_run()` 每次 gRPC 调用都 `subprocess.run(grpcurl.exe ...)`（Windows 每次 ~100ms+ 进程开销）。搬移流水线是递归遍历：500 子目录 = 500 次进程拉起；`FileMover._resolve_video_folder()` 每个 batch 还要逐分卷目录 `get_sub_files` 数文件 → 300 个单文件父目录可累积 1200+ 次子进程。grpcio 持久 channel 消除 90%+ 开销。

## 改造范围（原 4 处独立 grpcurl 子进程实现）

1. `mover/cd2_client.py` — 主封装，含流式 JSON 手工解析（`json.JSONDecoder().raw_decode` 循环）
2. `stash/delete.py` — `subprocess.run`，删除文件
3. `stash/cd2_offline.py` — `asyncio.create_subprocess_exec`，AddOfflineFiles 磁力添加
4. `stash/cd2_offline_check.py` — `asyncio.create_subprocess_exec`，离线任务轮询

## 实际落地形态（与计划的不同点）

- **项目迁移到 NAS 容器（2026-08-07 起唯一运行环境）**：`{DATA_VOLUME}/tools/{STASH_CONTAINER}/`（app/ 代码 + Dockerfile + compose，容器 {STASH_CONTAINER}，python:3.12-slim）。原 Windows git 主仓库 `{USER_PROFILE}\Documents\{PROJECT_NAME}\{STASH_CONTAINER}-v3` 已不可访问；NAS 目录无 .git，改代码前备份到 `{DATA_VOLUME}/tools/backups/<日期>/`
- **新客户端在项目根** `cd2_client.py`（非 mover/ 下）：`CD2Client(server, token, timeout=60)` 类 +
  模块级线程安全单例 `get_cd2_client()`（`threading.Lock` 惰性创建，读 Config）。
- `mover/cd2_client.py` **删除**；`mover/handler.py` 改 `from cd2_client import get_cd2_client`；
  `mover/__init__.py` 改从根模块 re-export。
- 异步调用方（delete/cd2_offline/cd2_offline_check）用 `asyncio.to_thread(get_cd2_client().xxx, ...)` 包裹阻塞调用。
- **返回 dict 保持旧 grpcurl JSON 键名**（`id/name/fullPathName/size/isDirectory`、`success/errorMessage`、
  `offlineFiles/pageCount`），调用方零改动。
- proto 重新从官网下载（v1.0.13，96KB），生成 `clouddrive_pb2*.py` 放项目根并加入 .gitignore。
- 顺带修正 config.py `CONFLICT_POLICY` 注释（0=覆盖 1=重命名 2=跳过）。

## 实测验证（直连 {CD2_HOST}:{CD2_GRPC_PORT}，可复用为验收清单）

| 探针 | 用途 | 结果 |
|---|---|---|
| `GetSystemInfo`（empty_pb2.Empty()，免鉴权） | 连通性 + proto 兼容 | ✅ SystemReady=True |
| `get_file_info(监控目录)`（FindFileByPath） | 鉴权 + 字段转换 | ✅ 返回 id/name/isDirectory |
| `get_sub_files(目录, force_refresh=True)` | 流式迭代 + 真实数据 | ✅ 非空目录返回 22 条 |
| `list_all_offline_files(page=1)` | 分页结构 | ⚠️ 服务端报错，见下 |

`ListAllOfflineFiles` 报 `NOT_FOUND: cloud account not found`——**用旧 grpcurl 原样跑同一请求同样报错**，
确认是 CD2 服务端云账户状态问题（需在 CD2 界面排查），非客户端回归。`ListOfflineFilesByPath` 与
带 `cloudName` 的变体当时也失败。诊断原则：新客户端报错先对照旧实现，同错即预存问题。

## 评审发现（部分已修，剩余为后续优化点）

- ✅ 已修：config.py `CONFLICT_POLICY` 注释错误（「2=覆盖」实为跳过；`Overwrite=0, Rename=1, Skip=2`）
- ⬜ 未修：`cleanup_empty_dirs` 两遍全树遍历 → 用一次遍历的 `dir→entries` 映射做空目录判断
- ⬜ 未修：`DeleteFiles`（MultiFileRequest）批量删空目录
- ⬜ 未修：`scan_all_dirs_and_files` 用 `queue.pop(0)`（O(n)）→ `collections.deque`
- ⬜ 未修：`FileMover._resolve_video_folder` 每个 batch 重新数分卷文件数 → 缓存当前分卷+余量

## 官方文档要点

- proto 下载：`https://www.clouddrive2.com/api/clouddrive.proto`（v1.0.13，2026-07-23 文档）
- 1.0.11→1.0.13 变更全在备份功能（backupQueueHighWater/LowWater/maxConcurrentBackupWalkers、
  useTempFileForCrossCloudCopy、BackupStatus `Waiting=6`），文件操作/离线下载 API 无变化
- Python 官方示例 = 持久 channel + Bearer metadata + 流式 for 循环，与落地形态一致
- 认证首选 API 令牌；8 个公开方法免认证（GetSystemInfo 可用于探测）
