#!/usr/bin/env python3
"""stash2Alist CLI 入口

用法:
    python -m stash2Alist                     # 默认加载 config.yaml
    python -m stash2Alist --config /path/to/config.yaml
    python -m stash2Alist --host 0.0.0.0 --port 8000
    python -m stash2Alist --debug             # 调试模式，打印详细日志
"""
import sys
import os
import argparse
import logging

import uvicorn

from .app import create_app

# 默认配置路径（优先取环境变量 STASH2ALIST_CONFIG）
DEFAULT_CONFIG = os.environ.get(
    "STASH2ALIST_CONFIG",
    os.path.join(os.path.dirname(__file__), "config.yaml"),
)


def main():
    parser = argparse.ArgumentParser(description="stash2Alist - Stash 流媒体透明代理到 Alist 直链")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="配置文件路径（默认: config.yaml）")
    parser.add_argument("--host", default=None, help="监听地址（覆盖配置）")
    parser.add_argument("--port", type=int, default=None, help="监听端口（覆盖配置）")
    parser.add_argument("--debug", action="store_true", help="调试模式，打印每个请求的详细信息")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志输出")
    args = parser.parse_args()

    # 日志配置
    log_level = logging.DEBUG if args.debug else (logging.INFO if not args.verbose else logging.DEBUG)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # 关闭 httpx 和 requests 的调试日志（避免刷屏）
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    # 检查配置文件
    config_path = args.config
    if not os.path.exists(config_path):
        print(f"错误: 配置文件不存在: {config_path}")
        print(f"提示: 可通过环境变量 STASH2ALIST_CONFIG 指定路径，或使用 --config 参数")
        sys.exit(1)

    # 创建应用（传递 debug 参数）
    app = create_app(config_path, debug=args.debug)

    # 从配置读取服务器参数（CLI 参数优先）
    with open(config_path, "r", encoding="utf-8") as f:
        import yaml
        config = yaml.safe_load(f)

    server_cfg = config.get("server", {})
    host = args.host or server_cfg.get("host", "0.0.0.0")
    port = args.port or server_cfg.get("port", 8000)

    print()
    print(f"  stash2Alist v{__import__('stash2Alist').__version__}")
    print(f"  Stash:   {config.get('stash', {}).get('url', 'N/A')}")
    print(f"  Alist:   {config.get('alist', {}).get('url', 'N/A')}")
    print(f"  监听地址: http://{host}:{port}")
    print(f"  信息接口: http://{host}:{port}/info")
    print(f"  路径映射: {len(config.get('path_mappings', []))} 条规则")
    print(f"  调试模式: {'✔ 开启' if args.debug else '关闭'}")
    print()

    log_level_str = "debug" if args.debug else "warning"
    uvicorn.run(app, host=host, port=port, log_level=log_level_str, access_log=args.debug)


if __name__ == "__main__":
    main()
