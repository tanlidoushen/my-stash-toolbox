# CD2 gRPC API 调试环境搭建（Docker）

在 Docker 容器中搭建 CD2 gRPC API 调试环境，适用于快速验证 API 调用、开发自动化脚本。

## 方案一：自建容器（推荐）

### Dockerfile

```dockerfile
FROM python:3.12-slim

RUN pip install grpcio grpcio-tools

# 下载 CD2 proto
ADD https://www.clouddrive2.com/api/clouddrive.proto /app/clouddrive.proto

# 生成 Python 桩代码
RUN python -m grpc_tools.protoc -I/app --python_out=/app --grpc_python_out=/app /app/clouddrive.proto

WORKDIR /app
CMD ["python3"]
```

构建并进入容器：

```bash
docker build -t cd2-grpc-client .
docker run -it --rm --network host \
  -e CD2_HOST=127.0.0.1 \
  -e CD2_GRPC_PORT=19798 \
  -e CD2_TOKEN=your_token_here \
  cd2-grpc-client
```

> `--network host` 使容器可直接访问宿主机 `127.0.0.1:19798`（CD2 默认 gRPC 端口）。若 CD2 在其他机器，改用 `--network bridge` 并将 `CD2_HOST` 设为目标 IP。

### 容器内验证

```python
import os
import grpc
import clouddrive_pb2 as pb2
import clouddrive_pb2_grpc

host = os.environ.get("CD2_HOST", "127.0.0.1")
port = os.environ.get("CD2_GRPC_PORT", "19798")
token = os.environ.get("CD2_TOKEN", "")

channel = grpc.insecure_channel(f"{host}:{port}")
stub = clouddrive_pb2_grpc.CloudDriveFileSrvStub(channel)
metadata = [("authorization", f"Bearer {token}")]

# 验证连通性
info = stub.GetSystemInfo(pb2.Empty())
print("System ready:", info.SystemReady)
```

## 方案二：直接使用已部署环境的容器

如果已有运行 grpcio + clouddrive_pb2 的容器，可直接 exec 进入：

```bash
docker exec -it <container> python3
```

容器内：

```python
import os
import grpc
import clouddrive_pb2 as pb2
import clouddrive_pb2_grpc

# 直连 CD2（host 网络模式）
stub = clouddrive_pb2_grpc.CloudDriveFileSrvStub(
    grpc.insecure_channel("127.0.0.1:19798")
)
metadata = [("authorization", f"Bearer {os.environ['CD2_TOKEN']}")]

# 快速验证连通性
stub.GetSystemInfo(pb2.Empty())
```

## 常用 API 调试示例

### 列出目录内容

```python
files = []
for resp in stub.GetSubFiles(pb2.ListSubFileRequest(
    path="/115", forceRefresh=False
), metadata=metadata):
    for f in resp.subFiles:
        print(f.name, f.isDirectory, f.size)
```

### 获取目录统计

```python
props = stub.GetFileDetailProperties(
    pb2.FileRequest(path="/115/xxx"),
    metadata=metadata
)
print(f"文件: {props.totalFileCount}, "
      f"文件夹: {props.totalFolderCount}, "
      f"大小: {props.totalSize}")
```

### 创建文件夹

```python
stub.CreateFolder(pb2.CreateFolderRequest(
    parentPath="/115",
    folderName="new_folder"
), metadata=metadata)
```

### 获取文件 SHA1 哈希

```python
for resp in stub.GetSubFiles(pb2.ListSubFileRequest(
    path="/115/xxx", forceRefresh=False
), metadata=metadata):
    for f in resp.subFiles:
        sha1 = f.fileHashes.get(2)  # key 2 = SHA1
        if sha1:
            print(f.name, sha1)
```

## 认证方式

- 除 `GetSystemInfo`、`GetToken`、`Login` 等 8 个公开方法外，全部需 `Authorization: Bearer <token>` 元数据头
- 推荐使用 API 令牌（可在 CD2 Web 界面生成），而非用户名/密码

## 注意事项

- 每脚本只建一个 gRPC channel（持久连接复用），避免反复创建连接
- `forceRefresh: true` 会强制云盘刷新，循环/递归遍历时尽量设为 false
- gRPC 错误信息用 `e.details()` 提取，不要直接 `str(e)`
- 流式响应（GetSubFiles、GetSearchResults）需用 for 循环迭代
- `AddOfflineFileRequest.urls` 是单个 string，传一个磁力链接即可