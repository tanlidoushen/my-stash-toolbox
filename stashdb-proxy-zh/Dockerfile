FROM golang:1.26-alpine AS builder
ARG GOPROXY=https://goproxy.cn,direct
ENV GOPROXY=${GOPROXY}
WORKDIR /build
COPY . .
RUN ./build.sh && CGO_ENABLED=0 go build -o /app/stashdb-proxy .

FROM alpine:3.20
RUN apk add --no-cache ca-certificates tzdata
WORKDIR /app
COPY --from=builder /app/stashdb-proxy .
EXPOSE 8900
ENTRYPOINT ["/app/stashdb-proxy"]
