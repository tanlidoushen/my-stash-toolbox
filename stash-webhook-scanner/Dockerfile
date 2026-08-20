# stash-webhook-scanner 镜像
# grpcio>=1.83 / protobuf>=7.35 匹配内置 python-clouddrive-client 的 gencode
# (CloudDrive.proto v1.0.13 生成的 pb2 要求 grpcio>=1.83.0)
FROM python:3.12-slim

ENV TZ=Asia/Shanghai

WORKDIR /app

# 先装依赖（利用层缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt \
    && pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple "grpcio>=1.83.0" "protobuf>=7.35.0"

# 拷贝应用代码
COPY . .

EXPOSE 9991

CMD ["python", "app.py"]
