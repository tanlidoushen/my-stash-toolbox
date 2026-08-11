# CloudDrive2 gRPC API

## Overview

CloudDrive2 (CD2) 云盘服务提供 gRPC API（HTTP/2 明文端口），用于文件/文件夹操作、云盘管理、磁力离线下载、传输任务监控。服务：`clouddrive.CloudDriveFileSrv`，包名 `clouddrive`，proto 文件 `clouddrive.proto`。

CD2 服务器所在地址为 `{CD2_HOST}`，gRPC 端口为 `{CD2_GRPC_PORT}`。可通过 gRPC 接口进行文件操作、自动化脚本（刮削/归类/磁力下载/直链服务等）等任务。

## When to Use

- 编写/修改调用 CD2 gRPC 的脚本（grpcurl 子进程或 Python grpcio）
- 文件搬移、删除、建目录、搜索、磁力离线下载、离线任务轮询
- 排查 CD2 调用失败（路径前缀、认证头、流式解析、conflictPolicy 语义）

## 资源位置

- **官方中文 API 指南**：官方文档站（clouddrive2.com 文档/API 页），或下载 proto 后 `protoc --decode` 查看
- **proto 官方下载**：`https://www.clouddrive2.com/api/clouddrive.proto`（当前 **v1.0.13**，96,056 字节，官网最新版）
- **完整方法清单**：本文内 `references/methods.md` — 官方 proto 解析出的全部 **226 个活跃 RPC**，按指南章节分类，含请求/响应类型（可离线查方法是否存在，无需下载 proto）
- **grpcurl**：已废弃（推荐使用 grpcio）；如需对照诊断，可在容器内 `apt install grpcurl` 或用 Python grpcio（见下）
- **⭐ 最快捷路径**：使用已配置好 grpcio + proto 的容器环境：
  - `docker exec <container> python3 -c "...grpc 脚本..."`
  - CD2 服务器用 `127.0.0.1:{CD2_GRPC_PORT}`（host 网络直连），token 通过环境变量 `os.environ['CD2_TOKEN']` 传入
  - 容器内已有 `clouddrive_pb2*`、grpcio、grpc_tools，脚本里 `import clouddrive_pb2 as pb2` 直接用
  - 一句话验证连通：`stub.GetSystemInfo(Empty())`（免认证方法），返回 `IsLogin: True / SystemReady: True` 即通
- 版本：proto 现为 **1.0.13**；1.0.11→1.0.13 的 API 变更全部在备份功能（backupQueueHighWater/LowWater/maxConcurrentBackupWalkers、useTempFileForCrossCloudCopy、BackupStatus `Waiting=6`），文件操作/离线下载 API 无变化

## 认证

- 除 8 个公开方法外全部需要 `Authorization: Bearer <token>` 元数据头
- grpcurl：`-H "Authorization:Bearer <token>"`
- grpcio：`metadata = [("authorization", "Bearer %s" % token)]`
- 推荐 API 令牌（细粒度权限、可撤销），而非用户名/密码 `GetToken`
- 免认证方法：`GetSystemInfo` `GetToken` `Login` `LoginWithThirdPartyAccount` `Register` `SendResetAccountEmail` `ResetAccount` `GetApiTokenInfo`

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
| GetFileDetailProperties | `FileRequest` | `path`, `forceRefresh`(可选) → **目录统计** |
| CreateFolder | `CreateFolderRequest` | `parentPath`, `folderName` |
| MoveFile | `MoveFileRequest` | `theFilePaths[]`, `destPath`, `conflictPolicy`, `moveAcrossClouds`(可选), `handleConflictRecursively`(可选) |
| DeleteFile | `FileRequest` | `path`, `forceRefresh`(可选) |
| DeleteFiles（批量） | `MultiFileRequest` | `path[]` |
| RenameFiles（批量） | `RenameFilesRequest` | `renameFiles[]`（`theFilePath`+`newName`） |
| GetSearchResults（流式） | `SearchRequest` | `path`, `searchFor`, `forceRefresh`, `fuzzyMatch`, `contentSearch` |
| AddOfflineFiles | — | `urls`(magnet), `toFolder` |
| ListAllOfflineFiles | — | `page`(分页，用 `pageCount` 判断是否还有下一页) |
| GetOfflineQuotaInfo | `OfflineQuotaRequest` | 离线下载配额/剩余 |
| GetSpaceInfo | `FileRequest` | 空间信息（`SpaceInfo`） |
| GetWebhookConfigs | — | 列出 Webhook 配置（`WebhookList`） |
| AddWebhookConfig / ChangeWebhookConfig / RemoveWebhookConfig | `WebhookRequest` / `StringValue` | 增改删 Webhook 配置 |
| GetWebhookConfigTemplate | — | 获取 Webhook 配置模板（`StringResult`） |

> 完整 226 个 RPC 的清单（含请求/响应类型、按指南分类）见 `references/methods.md`。

## GetFileDetailProperties：目录统计

**用途**：获取目录的服务器端统计（文件总数/文件夹总数/总大小），无需自己递归遍历，服务器算好直接返回。

- 方法：`GetFileDetailProperties(FileRequest) → FileDetailProperties`
- 请求：`FileRequest{path, forceRefresh?}`（path 为目录完整路径）
- 响应字段：
  ```protobuf
  int64 totalFileCount = 1;    // 文件总数（含嵌套所有层）
  int64 totalFolderCount = 2;  // 文件夹总数（含嵌套所有层）
  int64 totalSize = 3;         // 总大小 bytes
  bool   isFaved = 4;          // 是否收藏
  bool   isShared = 5;         // 是否分享
  string originalPath = 6;     // 原始路径
  ```
- 示例（如 `/cloud/path`）：返回 `totalFileCount, totalFolderCount, totalSize, originalPath` 等字段
- **适用场景**：清理辅助程序里要给每个目录标注"多大/多少文件"，用这个方法一次调用即可，别自己递归（尤其深层嵌套目录结构）
- `FindFileByPath` 返回单文件/目录自身属性（id/时间/类型/哈希），**不含统计**；要统计必须 `GetFileDetailProperties`

> ⚠️ 注意：GetSubFiles/FindFileByPath 对目录返回的 `size` 字段恒为 0（目录本身大小），需用 GetFileDetailProperties 拿 totalSize。

## RestartService：重启 CD2 软件

等效于 CD2 Web 界面「重启软件」：容器内进程重启，容器本身不重启（StartedAt/RestartCount 不变）。

- 方法：`RestartService`，请求/响应都是 `google.protobuf.Empty`
- **grpcio 调用**（推荐，grpcurl 含 "Restart" 字样的命令可能被网关防护误拦）：

```python
import grpc, clouddrive_pb2_grpc
from google.protobuf.empty_pb2 import Empty   # ⚠️ Empty 不在 clouddrive_pb2 里！用 google.protobuf.empty_pb2

stub = clouddrive_pb2_grpc.CloudDriveFileSrvStub(grpc.insecure_channel("{CD2_HOST}:{CD2_GRPC_PORT}"))
stub.RestartService(Empty(), metadata=[("authorization", "Bearer %s" % token)])
```

- **成功信号是 gRPC 错误**：返回 `UNAVAILABLE: Stream removed (End of TCP stream)` 即正常——CD2 收到命令立刻断开连接开始重启，EOF 不是失败
- **验证重启已发生**：`docker logs <container> --timestamps --since 15m | grep -E "welcome|initialized"` 出现新时间戳（CD2 启动日志 `welcome to clouddrive ...` + `database initialized`）
- CD2 容器软件重启由系统管理，容器本身的 `StartedAt`/`RestartCount` 不变，只能靠日志或挂载状态变化确认

## MoveFile ConflictPolicy 枚举

```protobuf
enum ConflictPolicy { Overwrite = 0; Rename = 1; Skip = 2; }
```

- **0=覆盖, 1=重命名, 2=跳过**
- 旧脚本/注释常误写为「1=自动重命名, 2=覆盖」——2 实际是跳过（文件不动），0 才是覆盖。默认 1 是安全值
- 搬整个目录树时开 `handleConflictRecursively: true` 处理文件夹冲突

## Python grpcio 客户端（官方推荐，替代 grpcurl 子进程）

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

**字段命名坑**：生成代码的 Python 字段名与 .proto 文件**逐字一致**——camelCase 保留（`isDirectory`、`fullPathName`、`theFilePaths`、`percendDone`、`infoHash`），个别 snake_case（`add_time`）。给业务层返回 dict 时保持旧 grpcurl JSON 键名（`id/name/fullPathName/size/isDirectory`），调用方零改动。
`AddOfflineFileRequest.urls` 是**单个 string**（非 repeated），传一个磁力串即可。

**与异步代码混用**：阻塞的 gRPC 调用在 asyncio 上下文用 `asyncio.to_thread` 包裹；channel 线程安全，可做模块级单例供 Flask/bot 线程共用。

## 备份/同步任务（Backup API）

**用途**：CD2 的"同步"功能 = 备份任务（源目录→目标目录，可设扩展名过滤、完成后删源=移动语义）。可用于"网盘→本地存储"的文件搬运。

### RPC 清单
| 方法 | 请求 | 说明 |
|---|---|---|
| `BackupGetAll` | Empty | 列出所有备份任务（含完整配置 + 状态）|
| `BackupGetStatus` | StringValue(源路径) | 单任务状态 |
| `BackupAdd` | Backup | 新建任务 |
| `BackupUpdate` | Backup | 更新配置 |
| `BackupRemove` | StringValue(源路径) | 删除任务 |
| `BackupSetEnabled` | BackupSetEnabledRequest(sourcePath, isEnabled) | 启用/禁用 |
| `BackupRestartWalkingThrough` | StringValue | 强制重新扫描 |
| `BackupAddDestination` / `BackupRemoveDestination` | BackupModifyRequest | 增删目标 |

### Backup 消息字段（关键）
```python
clouddrive_pb2.Backup(
    sourcePath="/115/xxx",
    destinations=[clouddrive_pb2.BackupDestination(destinationPath="/local/path/...", isEnabled=True)],
    fileBackupRules=[clouddrive_pb2.FileBackupRule(extensions="jpg,json,nfo,png")],  # oneof: extensions/fileNames/regex/minSize
    fileReplaceRule=clouddrive_pb2.FileReplaceRule.Skip,        # 0=Skip 1=Overwrite 2=KeepHistoryVersion
    fileDeleteRule=clouddrive_pb2.FileDeleteRule.Recycle,       # 0=Delete 1=Recycle 2=Keep 3=MoveToVersionHistory
    fileCompletionRule=clouddrive_pb2.FileCompletionRule.DeleteSource,  # 0=None 1=DeleteSource(移动) 2=DeleteSourceAndEmptyFolder
    isEnabled=False,
    fileSystemWatchEnabled=False,
    syncDeleteFromDest=False,      # 完整扫描时删目标端多余文件（镜像式）
    dontStartScanAfterAdd=True,    # 添加后不自动全量扫描（先确认配置再启用）
)
```

### BackupStatus.Status 枚举
`Idle=0` `WalkingThrough=1` `Error=2` `Disabled=3` `Scanned=4` `Finished=5` `Waiting=6`

### 已知问题
1. **extensions 过滤必须开 `isEnabled=True`**：FileBackupRule 有 4 个隐藏开关字段（proto 编号 100-103）：`isEnabled`(100, 默认 false=规则不生效)、`isBlackList`(101, false=白名单/true=黑名单)、`applyToFolder`(102)、`applyToFile`(103)。只设 extensions 不设 isEnabled=True → 规则静默失效，备份任务会处理源目录所有文件（含视频）。正确写法：
   ```python
   clouddrive_pb2.FileBackupRule(
       extensions="jpg,json,nfo,png",
       isEnabled=True,     # 必须！否则规则不生效
       isBlackList=False,  # False=白名单(只处理这些), True=黑名单(排除这些)
       applyToFile=True,
   )
   ```
2. **GetUploadFileList 默认返回空**：必须 `getAll=True` 才返回全量任务
3. **传输任务方向**：网盘→本地的备份，在上传任务列表里 key/dest 显示为**目标路径**
4. **取消后计数不立即归零**：`CancelAllUploadFiles` 异步；配合 `BackupSetEnabled(False)` 禁用任务后计数才归零
5. **UploadFileInfo.Status 枚举**：WaitforPreprocessing=0 Preprocessing=1 Cancelled=2 Transfer=3 Pause=4 Finish=5 Skipped=6 Inqueue=7 Ignored=8 Error=9 FatalError=10
6. **传输任务全量 RPC**：GetAllTasksCount / GetUploadFileList(getAll=True) / CancelAllUploadFiles / CancelUploadFiles(MultpleUploadFileKeyRequest{keys[]}) / PauseAllUploadFiles / ResumeAllUploadFiles

### 典型配置：网盘非视频文件→本地存储
- **关键配置**：`FileBackupRule(extensions="jpg,json,nfo,png", isEnabled=True, isBlackList=False, applyToFile=True)` + `fileCompletionRule=DeleteSource`（移动语义）+ `fileReplaceRule=Skip` + `fileDeleteRule=Recycle`
- **流程**：BackupAdd(dontStartScanAfterAdd=True) → BackupGetAll 核对配置 → BackupSetEnabled(True) → 若一定时间无任务生成，用 `BackupRestartWalkingThrough` 强制重新扫描 → 传输完成后 GetAllTasksCount 归零、BackupGetStatus=4(Scanned)
- **验证**：GetUploadFileList(getAll=True) 查看任务扩展名分布，确认只包含预期文件类型；源目录目标文件消失、保留文件仍在；目标目录结构一致
- **善后**：任务可保持 enabled（幂等，目标已有文件 Skip 跳过）；`BackupRemove(StringValue(源路径))` 彻底删除

## 批量 API 机会

- `DeleteFiles`：一次删多个路径（清理空目录时替代逐目录 `DeleteFile`）
- `RenameFiles`：批量重命名

## 离线任务状态

`OFFLINE_DOWNLOADING` 下载中 / `OFFLINE_FINISHED`·`OFFLINE_COMPLETED` 完成 / `OFFLINE_ERROR` 错误 / `OFFLINE_PENDING`·`OFFLINE_WAITING` 等待 / `OFFLINE_PAUSED` 暂停 / `OFFLINE_CANCELLED` 取消。任务字段：`name` `status` `percendDone`(0-100) `size` `parentId` `infoHash` `fileId` `url`。

**grpcio 枚举形态差异**：pb2 的 `status` 是 **int**（`0=OFFLINE_INIT 1=OFFLINE_DOWNLOADING 2=OFFLINE_FINISHED 3=OFFLINE_ERROR 4=OFFLINE_UNKNOWN`），而旧 grpcurl JSON 输出枚举**名字**。grpcio 客户端必须在序列化层做 int→名字映射，否则下游按名字判断（`is_finished = status in ("OFFLINE_FINISHED", ...)`）永远 False。

## 路径约定

- Stash 内路径：`/netdisk/CloudDrive/115/...`；CD2 虚拟路径：`/115/...`
- 转换：去掉 `CD2_STRIP_PREFIX`（`/netdisk/CloudDrive`）前缀，其余保留

## fileHashes：文件 SHA1 哈希

**用途**：CD2 直接返回文件的服务器端哈希，**无需下载文件算哈希**（CD2 上文件可能几十 GB，本地算 MD5/SHA1 不现实）。用于查重：两文件哈希相同即同一文件。

- **`GetSubFiles` 对文件项直接返回 `fileHashes`**（字段 `fileHashes`，map<uint32,string>），零额外调用成本
- **`FindFileByPath` 同样返回**（目录的 fileHashes 为空，只有文件有）
- proto 哈希类型枚举：
  ```protobuf
  enum HashType { Unknown=0; Md5=1; Sha1=2; PikPakSha1=3; }
  ```
- 例如：`fileHashes = {2: '<40位hex>'}` → **key 2 = SHA1**（40 位 hex）
- 用法：`f.fileHashes.get(2)` 取 SHA1，`f.fileHashes.get(1)` 取 MD5（若有）
- 查重场景：遍历目录收集每个文件 SHA1 → 按 SHA1 分组 → 相同即重复 → 按 size 排序看浪费空间。比下载算哈希高效几个数量级

## downloadUrlPath：下载直链

**用途**：文件的下载直链（带 token），可直接 HTTP 下载，支持 Range 断点续传。

- **`GetSubFiles`/`FindFileByPath` 对文件项返回 `downloadUrlPath`**（目录为空）
- 返回的是**相对路径 + 占位符**：`/static/{SCHEME}/{HOST}/{PREVIEW}/<urlencoded路径>?token=<token>`
- **必须拼接成完整 URL**（proto 注释：把 gRPC server 的 scheme://host:port 结合）：
  - `{SCHEME}` → `http` 或 `https`
  - `{HOST}` → gRPC 服务器地址（本机 `127.0.0.1:{CD2_GRPC_PORT}`）
  - `{PREVIEW}` → `false`（false=实际文件下载，true=预览）
  - 例：`http://127.0.0.1:{CD2_GRPC_PORT}/static/http/127.0.0.1:{CD2_GRPC_PORT}/false/115%2F...?token=...`
- 响应特性：HEAD 返回 200，`Content-Length` 与 size 一致，`Content-Disposition: attachment; filename=...`；GET 带 Range 返回 206
- **适用**：把 CD2 文件下载到本地处理、导出；支持断点续传适合大文件

## 向 CD2 云盘复制本地文件

### 场景
本地文件需要复制到网盘对应目录，供媒体服务器扫描入库。

### 流程
1. **确认目标目录是否存在** — 用 `GetSubFiles` 检查 CD2 虚拟路径：
   ```python
   for resp in stub.GetSubFiles(pb2.ListSubFileRequest(path='/cloud/path/to/target', forceRefresh=False), metadata=meta):
       files.extend(resp.subFiles)
   ```
   → 如果报 `NOT_FOUND`，说明目录不存在

2. **创建缺失目录** — 用 `CreateFolder`：
   ```python
   stub.CreateFolder(pb2.CreateFolderRequest(parentPath='/cloud/parent', folderName='new_folder'), metadata=meta)
   ```

3. **通过 CloudNAS FUSE 挂载点复制文件** — CD2 的 CloudNAS 挂载在宿主机，直接 `cp` 文件进去，CD2 会自动同步到云端：
   ```bash
   cp /local/path/to/file.mkv \
     "{CLOUDNAS_MOUNT_PATH}/115/cloud/target/path/"
   ```

4. **验证** — 通过 CloudNAS 挂载点 `ls -lh` 确认文件可见，或通过 gRPC 再次 `GetSubFiles` 验证

### 注意事项
- `cp` 到 CloudNAS 挂载点时，如果目标目录还没在 FUSE 中刷新，`cp` 会报 `No such file or directory`。先 `CreateFolder` 创建目录，等 FUSE 刷新后再 `cp`
- 文件写入 CloudNAS 后，CD2 会自动检测并同步到云端，不需要手动触发上传
- 大文件 cp 到 FUSE 挂载点可能较慢，耐心等待
- 同步任务（Backup API）的 `destPath` 目录在 CD2 中可能不存在，需要通过 `CreateFolder` 手动创建

## Common Pitfalls

1. **conflictPolicy 语义**：0=覆盖, 1=重命名, 2=跳过——别把 2 当覆盖用
2. **流式 JSON 解析**：grpcurl 输出多对象，逐条 `raw_decode`
3. **Windows 路径（仅 grpcurl）**：`CD2_GRPCURL` 用原始字符串或双反斜杠（含空格路径）
4. **forceRefresh 开销**：`forceRefresh: true` 会强制云盘刷新，循环/递归遍历时尽量 false
5. **子进程性能**：每次 grpcurl = 一个 subprocess，递归遍历大目录树会累积数千次调用，建议迁移 grpcio 持久 channel
6. **新客户端报错先对照旧实现**：同请求用旧 grpcurl 原样跑一遍，错误相同 = 服务端预存问题而非客户端回归
7. **gRPC 错误信息处理（`grpc.RpcError`）**：
   - 要拿干净业务信息用 `e.details()`（如 115 `code: 10008, message: 任务已存在，请勿输入重复的链接地址`），不要直接 `str(e)`——`_InactiveRpcError` repr 超长且含尖括号
   - 若必须截断错误文本，长度要够（≥300）。`str(e)[:150]` 会把"任务已存在"（repr 第 ~165 字符处）切掉，导致下游按文本识别重复任务（is_dup）误判成"添加失败"
   - 该 repr 嵌入 Telegram HTML 消息会炸解析（`Can't parse entities: unsupported start tag`）——第三方来源字符串（错误信息、磁力名称）进 HTML 消息前先 `html.escape`
   - 例：重复添加磁力 → AddOfflineFiles 返回 INTERNAL + `code 10008 任务已存在`

## References

- `references/methods.md` — **完整 RPC 方法清单（v1.0.13，226 个）**：从官方 proto 解析，按官方指南分类，含请求/响应类型、流式标记、公共方法列表