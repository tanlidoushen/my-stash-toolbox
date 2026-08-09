# Stash GraphQL API 参考

> 本文档基于 Stash v0.31.1（databaseSchema / appSchema = 85）实测编写。不同版本 schema 可能有差异，使用前请先 introspection 确认。

## 端点与认证

- GraphQL 端点：`http://{STASH_SERVER}:9999/graphql`
- Playground（GraphiQL）：`http://{STASH_SERVER}:9999/playground`
- 所有请求 POST，`Content-Type: application/json`
- 认证：header `ApiKey: <key>`（Settings > Security > Authentication 生成）
- 未配置认证的实例可直接访问；配置后所有请求（含 WS 订阅）都要带 ApiKey header，否则 401
- 成功数据在 `data`；失败时响应含 `errors` 数组

```bash
curl -s -X POST -H "Content-Type: application/json" -H "ApiKey: <key>" \
  --data '{"query":"{ systemStatus { databaseSchema appSchema } }"}' \
  http://{STASH_SERVER}:9999/graphql
```

## Schema 概览（v0.31.1）

| 类型 | 数量 |
|------|------|
| Query | 74 |
| Mutation | 134 |
| Subscription | 3 |

### Query — 媒体查询

| 字段 | 说明 |
|------|------|
| `findScene(id, checksum)` | 按 ID 或 checksum 查单场景 |
| `findScenes(scene_filter, scene_ids, ids, filter)` | 场景列表 |
| `findScenesByPathRegex` / `findSceneByHash` / `findDuplicateScenes` | 路径正则/哈希/重复场景 |
| `findPerformer` / `findPerformers` | 演员 |
| `findStudio` / `findStudios` | 片商 |
| `findTag` / `findTags` | 标签 |
| `findGallery` / `findImage` / `findMovie` / `findGroup` / `findSceneMarkers` | 图册/图片/影片/分组/场景标记 |
| `allScenes` / `allPerformers` / `allStudios` / `allTags` / `allGalleries` / `allImages` / `allMovies` / `allSceneMarkers` | 无过滤全量 |

### Query — 文件/任务/系统

- 文件：`findFile(id, path)` / `findFiles(file_filter, filter, ids)` / `findFolder(id, path)` / `findFolders(...)`
- 任务：`findJob(input: FindJobInput!)` / `jobQueue()`
- 系统：`systemStatus()` / `version()` / `logs()` / `configuration()` / `directory(path, locale)` / `latestversion()`
- 统计：`stats()` / `markerStrings(q, sort)` / `sceneWall(q)` / `sceneStreams(id)` / `parseSceneFilenames(...)`

### Query — 刮削

- `scrapeSingleScene(source, input)` / `scrapeSceneURL(url)`
- `scrapeMultiScenes` / `scrapeMultiPerformers`
- `listScrapers(types)` / `plugins()` / `pluginTasks()`
- `validateStashBoxCredentials(input)`

### Mutation — 场景

- `sceneCreate(input)` / `sceneUpdate(input)` / `sceneDestroy(input)`
- `scenesDestroy` / `scenesUpdate` / `sceneMerge` / `sceneAssignFile`
- 标记：`sceneMarkerCreate` / `sceneMarkerUpdate` / `sceneMarkerDestroy` / `sceneMarkersDestroy`
- 播放历史：`sceneIncrementPlayCount` / `sceneResetPlayCount` / `sceneSaveActivity` / `sceneAddPlay` / `sceneDeletePlay` / `sceneAddO` / `sceneDeleteO` / `sceneIncrementO` / `sceneDecrementO` / `sceneResetO` / `sceneGenerateScreenshot`

### Mutation — 演员/片商/标签/图册

- 演员：`performerCreate` / `performerUpdate` / `performerDestroy` / `performersDestroy` / `performerMerge`
- 片商：`studioCreate` / `studioUpdate` / `studioDestroy` / `studiosDestroy`
- 标签：`tagCreate` / `tagUpdate` / `tagDestroy` / `tagsDestroy` / `tagsMerge`
- 图册：`galleryCreate` / `galleryUpdate` / `galleryDestroy` / `galleriesUpdate` / `addGalleryImages` / `removeGalleryImages` / `setGalleryCover` / `galleryChapterCreate/Destroy/Update`
- 图片/影片/分组：`imageUpdate` / `imageDestroy` / `imagesUpdate` / `imagesDestroy` / `movieCreate/Destroy/Update` / `groupCreate/Destroy/Update`
- 批量：`bulkSceneUpdate` / `bulkPerformerUpdate` / `bulkStudioUpdate` / `bulkTagUpdate` / `bulkImageUpdate` / `bulkGalleryUpdate` / `bulkMovieUpdate` / `bulkSceneMarkerUpdate` / `bulkGroupUpdate`

### Mutation — 元数据任务

| 字段 | 用途 |
|------|------|
| `metadataScan(input)` | 扫描（加 rescan 强制重扫） |
| `metadataIdentify(input)` | 刮削识别（stash-box/插件） |
| `metadataAutoTag(input)` | 自动打标签 |
| `metadataGenerate(input)` | 生成 preview/sprite/phashes 等 |
| `metadataClean(input)` / `metadataCleanGenerated(input)` | 清理 |
| `metadataExport()` / `metadataImport()` | 全量导出/导入 |
| `stopJob(job_id)` / `stopAllJobs()` | 停止任务 |

### Mutation — 文件 / stash-box / 系统

- 文件：`moveFiles(input)` / `deleteFiles(ids)` / `destroyFiles(ids)` / `fileSetFingerprints(input)`
- stash-box：`submitStashBoxFingerprints` / `submitStashBoxSceneDraft` / `submitStashBoxPerformerDraft` / `stashBoxBatchPerformerTag` / `stashBoxBatchStudioTag` / `stashBoxBatchTagTag`
- 系统：`execSQL(sql, args)` / `querySQL(sql, args)`（⚠️ 危险操作）、`generateAPIKey` / `backupDatabase` / `optimiseDatabase` / `configureGeneral/Interface/Scraping/DLNA/Defaults` / `setup(input)`
- 插件：`runPluginOperation` / `runPluginTask` / `reloadPlugins` / `reloadScrapers` / `setPluginsEnabled` / `installPackages` / `uninstallPackages` / `updatePackages`
- 保存过滤：`saveFilter` / `destroySavedFilter` / `setDefaultFilter`

### Subscription（3 个）

- `jobsSubscribe() -> JobStatusUpdate!` — 任务状态实时推送，连接 `ws://{STASH_SERVER}:9999/graphql`，header 带 ApiKey
- `loggingSubscribe() -> [LogEntry!]!`
- `scanCompleteSubscribe() -> Boolean!`

## 关键输入类型

### SceneUpdateInput

`id: ID!`、`title`、`code`、`details`、`director`、`url`、`urls`、`date`、`rating100`、`o_counter`、`organized`、`studio_id`、`performer_ids`、`tag_ids`、`gallery_ids`、`groups`、`movies`、`cover_image`（URL 或 base64）、`stash_ids`、`resume_time`、`play_duration`、`play_count`、`primary_file_id`、`custom_fields`

### ScanMetadataInput

`paths: [String!]`、`rescan: Boolean`（强制重扫）、`scanGenerateCovers`、`scanGeneratePreviews`、`scanGenerateImagePreviews`、`scanGenerateSprites`、`scanGeneratePhashes`、`scanGenerateImagePhashes`、`scanGenerateThumbnails`、`scanGenerateClipPreviews`、`filter: ScanMetaDataFilterInput`

### IdentifyMetadataInput

`sources: [IdentifySourceInput!]!`（有序，仅第一个命中的 source 生效）、`options: IdentifyMetadataOptionsInput`、`sceneIDs: [ID!]`、`paths: [String!]`

- `IdentifyFieldOptionsInput { field: String!, strategy: IdentifyFieldStrategy!, createMissing: Boolean }`
- 支持的 `field` 值（v0.31 为字符串，非枚举）：`TITLE`、`STUDIO`、`DATE`、`DETAILS`、`URLS`、`PERFORMERS`、`TAGS`、`STUDIO_CODE`、`DIRECTOR`、`STASH_IDS`、`IMAGE`、`COVER`

### PerformerCreateInput

`name: String!`、`disambiguation`、`url`、`urls`、`gender: GenderEnum`、`birthdate`、`ethnicity`、`country`、`eye_color`、`height_cm`、`measurements`、`fake_tits`、`penis_length`、`circumcised`、`career_length`、`career_start`、`career_end`、`tattoos`、`piercings`、`alias_list`、`twitter`、`instagram`、`favorite`、`tag_ids`、`image`、`stash_ids`、`rating100`、`details`、`death_date`、`hair_color`、`weight`、`ignore_auto_tag`、`custom_fields`

### 查询过滤

- `FindFilterType`：`q`（模糊搜索）、`page`、`per_page`（**-1 = 全部结果**，默认 25）、`sort`、`direction: SortDirectionEnum`
- `SceneFilterType`：`id/title/code/path/checksum/oshash/phash`（`StringCriterionInput { value, modifier }`）、`organized`、`rating100`、`duration`、`resolution`、`studios`、`performers`、`tags`、`stash_id_endpoint`、`is_missing`、`date`、`created_at/updated_at`、`AND/OR/NOT` 组合

## 常用枚举

- `JobStatus`：`READY / RUNNING / FINISHED / STOPPING / CANCELLED / FAILED`
- `IdentifyFieldStrategy`：`IGNORE / MERGE / OVERWRITE`
- `CriterionModifier`：`EQUALS / NOT_EQUALS / GREATER_THAN / LESS_THAN / IS_NULL / NOT_NULL / INCLUDES_ALL / INCLUDES / EXCLUDES / MATCHES_REGEX / NOT_MATCHES_REGEX / BETWEEN / NOT_BETWEEN`
- `GenderEnum`：`MALE / FEMALE / TRANSGENDER_MALE / TRANSGENDER_FEMALE / INTERSEX / NON_BINARY`
- `SortDirectionEnum`：`ASC / DESC`
- `ResolutionEnum`：`VERY_LOW(144p) / STANDARD_HD(720p) / FULL_HD(1080p) / FOUR_K / HUGE(8K+)`
- `PackageType`：`Scraper / Plugin`

## 常用操作示例

### 1. 扫描并等待完成

```graphql
mutation { metadataScan(input: { paths: ["/path/to/media"], rescan: true, scanGeneratePreviews: true, scanGeneratePhashes: true }) }
```
→ 返回 job id；用 `jobsSubscribe` WS 或轮询 `findJob` 等到 `FINISHED`/`FAILED`。

### 2. 按路径查场景

```graphql
query { findScenes(scene_filter: { path: { value: "/path/to/file.mkv", modifier: EQUALS } }) { count scenes { id title files { path size } } } }
```

### 3. 更新场景

```graphql
mutation { sceneUpdate(input: { id: "123", title: "ABC-123", code: "ABC-123", date: "2026-01-01", studio_id: "5", performer_ids: ["7","9"], tag_ids: ["2"], cover_image: "data:image/jpeg;base64,...", stash_ids: [{ endpoint: "https://stash-box.example.org/graphql", stash_id: "..." }] }) { id title } }
```

### 4. 创建演员

```graphql
mutation { performerCreate(input: { name: "Name", gender: FEMALE, alias_list: ["Alias"], image: "https://..." }) { id name } }
```

### 5. Python 调用

```python
import httpx
API = "http://{STASH_SERVER}:9999/graphql"

async def gql(query, variables=None, api_key=None):
    headers = {}
    if api_key:
        headers["ApiKey"] = api_key
    r = await httpx.AsyncClient().post(API, json={"query": query, "variables": variables or {}}, headers=headers)
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]
```

## 注意事项

1. **版本差异**：v0.31.1 中 `IdentifyFieldOptionsInput.field` 是 `String!`（非枚举）；旧版的 `ScanMode`、`IdentifyField` 枚举已不存在。写 Identify/Scan 前先 introspection 核实。
2. **API Key**：未配置认证的实例直接可访问；配置后所有请求（含 WS 订阅）都要带 `ApiKey` header。
3. **`per_page: -1`** 表示返回全部结果。
4. **cover_image/image 字段**传 URL 或 base64 data URL，不是本地文件路径。
5. **sceneDestroy 删盘**：`delete_file: true` 会物理删除文件；配合网盘挂载时需先取路径再走网盘 API 删除。
6. **任务串行**：Stash job 队列串行，多个 metadataScan/Identify 会排队。
7. **execSQL / querySQL 是危险操作**，schema 未知时勿乱用。
8. **响应结构**：GraphQL 错误在 `errors`，`data` 可能为 null；批量操作要逐个检查返回值。
