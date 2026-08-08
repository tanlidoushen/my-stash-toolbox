# stash-webhook-scanner 镜像
# 固定 grpcio/protobuf 版本以匹配 clouddrive_pb2.py 生成版本 (protobuf 5.29.0)
FROM python:3.12-slim

ENV TZ=Asia/Shanghai \
    HTTP_PROXY=http://<proxy-server>:7890 \
    HTTPS_PROXY=http://<proxy-server>:7890 \
    NO_PROXY=127.0.0.1,localhost,<internal-cidr>

WORKDIR /app

# 先装依赖（利用层缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir grpcio==1.71.0 protobuf==5.29.4

# 拷贝应用代码
COPY . .

EXPOSE 9991

CMD ["python", "app.py"]

