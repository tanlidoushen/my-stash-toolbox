# CloudDrive2 gRPC API

## Overview

CloudDrive2 (CD2) 云盘服务提供 gRPC API（HTTP/2 明文端口），用于文件/文件夹操作、云盘管理、磁力离线下载、传输任务监控。服务：`clouddrive.CloudDriveFileSrv`，包名 `clouddrive`，proto 文件 `clouddrive.proto`。

## 资源

- **proto 官方下载**：`https://www.clouddrive2.com/api/clouddrive.proto`（当前 **v1.0.13**）
- **完整方法清单**：`references/methods.md` — 226 个活跃 RPC，按指南章节分类，含请求/响应类型
- 1.0.11→1.0.13 的 API 变更仅限备份功能（backupQueueHighWater/LowWater/maxConcurrentBackupWalkers、useTempFileForCrossCloudCopy、BackupStatus `Waiting=6`），文件操作/离线下载 API 无变化

## 认证

- 除 8 个公开方法外全部需 `Authorization: Bearer <token>` 元数据头
- 推荐 API 令牌（细粒度权限、可撤销），而非用户名/密码方式
- 公开方法（免认证）：`GetSystemInfo` `GetToken` `Login` `LoginWithThirdPartyAccount` `Register` `SendResetAccountEmail` `ResetAccount` `GetApiTokenInfo`

## grpcurl 调用模板

```
grpcurl -plaintext -import-path <PROTO_PATH> -proto <PROTO_FILE> \
  -H "Authorization:Bearer <token>" -d '<json>' <SERVER> \
  clouddrive.CloudDriveFileSrv/<Method>
```

无 body 的方法省略 `-d`。**响应为流式 JSON**：可能返回多个独立 JSON 对象，必须用 `json.JSONDecoder().raw_decode` 循环逐条解析，不能整体 `json.loads()`。

## 核心方法速查

| 方法 | 请求消息 | 关键字段 |
|---|---|---|
| GetSubFiles（流式） | `ListSubFileRequest` | `path`, `forceRefresh`, `checkExpires`(可选) |
| FindFileByPath | `FindFileByPathRequest` | `parentPath`(通常"/"), `path` |
| GetFileDetailProperties | `FileRequest` | `path`, `forceRefresh`(可选) |
| CreateFolder | `CreateFolderRequest` | `parentPath`, `folderName` |
| MoveFile | `MoveFileRequest` | `theFilePaths[]`, `destPath`, `conflictPolicy`, `moveAcrossClouds`(可选), `handleConflictRecursively`(可选) |
| DeleteFile | `FileRequest` | `path`, `forceRefresh`(可选) |
| DeleteFiles（批量） | `MultiFileRequest` | `path[]` |
| RenameFiles（批量） | `RenameFilesRequest` | `renameFiles[]`（`theFilePath`+`newName`） |
| GetSearchResults（流式） | `SearchRequest` | `path`, `searchFor`, `forceRefresh`, `fuzzyMatch`, `contentSearch` |
| AddOfflineFiles | `AddOfflineFileRequest` | `urls`(magnet), `toFolder` |
| ListAllOfflineFiles | `OfflineFileListAllRequest` | `page`（分页，用 `pageCount` 判断下一页） |
| GetOfflineQuotaInfo | `OfflineQuotaRequest` | 离线下载配额/剩余 |
| GetSpaceInfo | `FileRequest` | 空间信息（`SpaceInfo`） |
| GetWebhookConfigs | `google.protobuf.Empty` | 列出 Webhook 配置 |
| AddWebhookConfig / ChangeWebhookConfig / RemoveWebhookConfig | `WebhookRequest` / `StringValue` | 增改删 Webhook 配置 |
| GetWebhookConfigTemplate | `google.protobuf.Empty` | 获取 Webhook 配置模板 |

## GetFileDetailProperties：目录统计

获取目录的服务器端统计（文件总数/文件夹总数/总大小），无需递归遍历。

- 请求：`FileRequest{path, forceRefresh?}`
- 响应：
  ```protobuf
  int64 totalFileCount = 1;    // 文件总数（含嵌套所有层）
  int64 totalFolderCount = 2;  // 文件夹总数（含嵌套所有层）
  int64 totalSize = 3;         // 总大小 bytes
  bool   isFaved = 4;          // 是否收藏
  bool   isShared = 5;         // 是否分享
  string originalPath = 6;     // 原始路径
  ```
- `FindFileByPath` 返回单文件/目录自身属性（id/时间/类型/哈希），**不含统计**
- 注意：GetSubFiles/FindFileByPath 对目录返回的 `size` 字段恒为 0，需用 GetFileDetailProperties 拿 totalSize

## RestartService：重启 CD2 软件

等效于 CD2 Web 界面「重启软件」：容器内进程重启，容器本身不重启。

- 方法：`RestartService(Empty) → Empty`
- 成功信号是 gRPC 错误 `UNAVAILABLE: Stream removed (End of TCP stream)`——CD2 收到命令立刻断开连接开始重启，EOF 不是失败

```python
import grpc, clouddrive_pb2_grpc
from google.protobuf.empty_pb2 import Empty

stub = clouddrive_pb2_grpc.CloudDriveFileSrvStub(grpc.insecure_channel("{CD2_HOST}:{CD2_GRPC_PORT}"))
stub.RestartService(Empty(), metadata=[("authorization", "Bearer %s" % token)])
```

## MoveFile ConflictPolicy 枚举

```protobuf
enum ConflictPolicy { Overwrite = 0; Rename = 1; Skip = 2; }
```

- **0=覆盖, 1=重命名(默认), 2=跳过**
- 旧脚本常误写为「1=自动重命名, 2=覆盖」——2 实际是跳过
- 搬整个目录树时开 `handleConflictRecursively: true`

## Python grpcio 客户端

```bash
pip install grpcio grpcio-tools
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. clouddrive.proto
```

```python
import grpc
import clouddrive_pb2, clouddrive_pb2_grpc

channel = grpc.insecure_channel("{CD2_HOST}:{CD2_GRPC_PORT}")
stub = clouddrive_pb2_grpc.CloudDriveFileSrvStub(channel)
metadata = [("authorization", "Bearer %s" % token)]

# 流式方法（GetSubFiles / GetSearchResults）
files = []
for resp in stub.GetSubFiles(clouddrive_pb2.ListSubFileRequest(path=p, forceRefresh=False), metadata=metadata):
    files.extend(resp.subFiles)
```

每脚本只建一个 channel（持久连接复用）；gRPC 错误为 `grpc.RpcError`。

**字段命名**：生成代码的 Python 字段名与 .proto 文件逐字一致——camelCase 保留（`isDirectory`、`fullPathName`、`theFilePaths`、`percendDone`、`infoHash`），个别 snake_case（`add_time`）。`AddOfflineFileRequest.urls` 是单个 string（非 repeated）。

## 备份/同步任务（Backup API）

CD2 的"同步"功能 = 备份任务（源目录→目标目录，可设扩展名过滤、完成后删源=移动语义）。

### RPC 清单
| 方法 | 请求 | 说明 |
|---|---|---|
| `BackupGetAll` | Empty | 列出所有备份任务 |
| `BackupGetStatus` | StringValue(源路径) | 单任务状态 |
| `BackupAdd` | Backup | 新建任务 |
| `BackupUpdate` | Backup | 更新配置 |
| `BackupRemove` | StringValue(源路径) | 删除任务 |
| `BackupSetEnabled` | BackupSetEnabledRequest | 启用/禁用 |
| `BackupRestartWalkingThrough` | StringValue | 强制重新扫描 |
| `BackupAddDestination` / `BackupRemoveDestination` | BackupModifyRequest | 增删目标 |

### Backup 消息字段
```python
clouddrive_pb2.Backup(
    sourcePath="/115/xxx",
    destinations=[clouddrive_pb2.BackupDestination(destinationPath="/local/path/...", isEnabled=True)],
    fileBackupRules=[clouddrive_pb2.FileBackupRule(extensions="jpg,json,nfo,png")],
    fileReplaceRule=clouddrive_pb2.FileReplaceRule.Skip,        # 0=Skip 1=Overwrite 2=KeepHistoryVersion
    fileDeleteRule=clouddrive_pb2.FileDeleteRule.Recycle,       # 0=Delete 1=Recycle 2=Keep 3=MoveToVersionHistory
    fileCompletionRule=clouddrive_pb2.FileCompletionRule.DeleteSource,  # 0=None 1=DeleteSource 2=DeleteSourceAndEmptyFolder
    isEnabled=False,
    fileSystemWatchEnabled=False,
    syncDeleteFromDest=False,
    dontStartScanAfterAdd=True,
)
```

### BackupStatus.Status 枚举
`Idle=0` `WalkingThrough=1` `Error=2` `Disabled=3` `Scanned=4` `Finished=5` `Waiting=6`

### 注意事项
- `FileBackupRule` 有 4 个隐藏开关字段（proto 编号 100-103）：`isEnabled`(100, 默认 false=规则不生效)、`isBlackList`(101, false=白名单/true=黑名单)、`applyToFolder`(102)、`applyToFile`(103)。只设 extensions 不设 isEnabled=True 则规则静默失效
- `GetUploadFileList` 必须 `getAll=True` 才返回全量任务
- `CancelAllUploadFiles` 异步，取消后计数不立即归零
- 传输任务全量 RPC：GetAllTasksCount / GetUploadFileList / CancelAllUploadFiles / CancelUploadFiles / PauseAllUploadFiles / ResumeAllUploadFiles

### UploadFileInfo.Status 枚举
WaitforPreprocessing=0 Preprocessing=1 Cancelled=2 Transfer=3 Pause=4 Finish=5 Skipped=6 Inqueue=7 Ignored=8 Error=9 FatalError=10

## 批量 API

- `DeleteFiles`：一次删多个路径
- `RenameFiles`：批量重命名

## 离线任务状态

`OFFLINE_DOWNLOADING` / `OFFLINE_FINISHED`·`OFFLINE_COMPLETED` / `OFFLINE_ERROR` / `OFFLINE_PENDING`·`OFFLINE_WAITING` / `OFFLINE_PAUSED` / `OFFLINE_CANCELLED`。任务字段：`name` `status` `percendDone`(0-100) `size` `parentId` `infoHash` `fileId` `url`。

**grpcio 枚举差异**：pb2 的 `status` 是 int（`0=OFFLINE_INIT 1=OFFLINE_DOWNLOADING 2=OFFLINE_FINISHED 3=OFFLINE_ERROR 4=OFFLINE_UNKNOWN`），而 grpcurl JSON 输出枚举名字。grpcio 客户端需在序列化层做 int→名字映射。

## 路径约定

- Stash 内路径：`/netdisk/CloudDrive/115/...`；CD2 虚拟路径：`/115/...`
- 转换：去掉 `CD2_STRIP_PREFIX`（`/netdisk/CloudDrive`）前缀

## fileHashes：文件 SHA1 哈希

CD2 直接返回文件的服务端哈希，无需下载文件。用于查重。

- `GetSubFiles`/`FindFileByPath` 对文件项返回 `fileHashes`（map<uint32,string>）
- `fileHashes = {2: '<40位hex>'}` → **key 2 = SHA1**
- 用法：`f.fileHashes.get(2)` 取 SHA1，`f.fileHashes.get(1)` 取 MD5（若有）
- 哈希类型枚举：`Unknown=0; Md5=1; Sha1=2; PikPakSha1=3`

## downloadUrlPath：下载直链

文件的下载直链（带 token），可直接 HTTP 下载，支持 Range 断点续传。

- `GetSubFiles`/`FindFileByPath` 对文件项返回 `downloadUrlPath`（目录为空）
- 返回格式：`/static/{SCHEME}/{HOST}/{PREVIEW}/<urlencoded路径>?token=<token>`
- 需拼接为完整 URL：`{SCHEME}://{HOST}/static/{SCHEME}/{HOST}/{PREVIEW}/<路径>?token=<token>`
- 响应：HEAD 200，`Content-Length` 与 size 一致，`Content-Disposition: attachment; filename=...`；GET 带 Range 返回 206

## Common Pitfalls

1. **conflictPolicy 语义**：0=覆盖, 1=重命名, 2=跳过——别把 2 当覆盖用
2. **流式 JSON 解析**：grpcurl 输出多对象，逐条 `raw_decode`
3. **forceRefresh 开销**：循环/递归遍历时尽量 false
4. **gRPC 错误信息（`grpc.RpcError`）**：用 `e.details()` 拿业务信息（如 `code: 10008, message: 任务已存在`），不要直接 `str(e)`

## References

- `references/methods.md` — 完整 RPC 方法清单（v1.0.13，226 个）