#!/usr/bin/env python3
"""Stash raw-plugin backend for Test Button Plugin.

All third-party HTTP traffic and filesystem writes are made from this process,
not from the UI.
The script receives one JSON value on stdin and writes one JSON value on stdout.
"""

import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPCookieProcessor
from http.cookiejar import Cookie, CookieJar

SUBTITLE_API = "https://api-shoulei-ssl.xunlei.com/oracle/subtitle"


def log(message):
    print(f"[TestBtn] {message}", file=sys.stderr, flush=True)


def request(url, method="GET", body=None, headers=None, timeout=45):
    req = Request(url, data=body, headers=headers or {}, method=method)
    with build_opener().open(req, timeout=timeout) as response:
        return response.read(), response.headers.get_content_charset() or "utf-8"


def stash_request(plugin_input, query, variables):
    connection = plugin_input.get("server_connection") or {}
    scheme = connection.get("Scheme") or "http"
    host = connection.get("Host") or "127.0.0.1"
    port = connection.get("Port") or 9999
    url = f"{scheme}://{host}:{port}/graphql"
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    cookie = connection.get("SessionCookie") or {}
    if cookie.get("Name") and cookie.get("Value"):
        headers["Cookie"] = f"{cookie['Name']}={cookie['Value']}"
    raw, _ = request(url, method="POST", body=payload, headers=headers)
    reply = json.loads(raw.decode("utf-8"))
    if reply.get("errors"):
        raise RuntimeError(reply["errors"][0].get("message", "Stash GraphQL request failed"))
    return reply["data"]


def scene(plugin_input, scene_id):
    query = """
      query FindScene($id: ID!) {
        findScene(id: $id) { id title code files { path } stash_ids { stash_id endpoint } }
      }
    """
    value = stash_request(plugin_input, query, {"id": str(scene_id)}).get("findScene")
    if not value or not value.get("files"):
        raise RuntimeError("未找到场景或该场景没有媒体文件")
    return value


def subtitle_name(scene_info):
    supported = ("javstash.org", "javdb.com")
    ids = scene_info.get("stash_ids") or []
    has_supported_id = any(any(site in (item.get("endpoint") or "") for site in supported) for item in ids)
    return (scene_info.get("code") or scene_info.get("title") or "") if has_supported_id else (scene_info.get("title") or "")


def search(keyword):
    url = f"{SUBTITLE_API}?{urlencode({'gcid': '', 'cid': '', 'name': keyword})}"
    raw, charset = request(url)
    data = json.loads(raw.decode(charset, errors="replace"))
    items = data if isinstance(data, list) else (data.get("data") or data.get("subtitles") or data.get("result") or [])
    if not isinstance(items, list):
        items = []
    # Never let the UI decide where to fetch from: return only attributes needed for display and an opaque URL.
    return [{
        "url": str(item.get("url") or item.get("download_url") or ""),
        "name": str(item.get("name") or item.get("filename") or f"字幕 {index + 1}"),
        "ext": str(item.get("ext") or item.get("format") or "srt"),
        "source": str(item.get("extra_name") or item.get("source") or "未知"),
    } for index, item in enumerate(items) if isinstance(item, dict)]


def fetch_subtitle(source_url):
    if not source_url.startswith(("https://", "http://")):
        raise RuntimeError("字幕下载地址无效")
    raw, charset = request(source_url, timeout=90)
    return raw, charset


def scan_path_for_metadata(plugin_input, path):
    """Trigger the same metadataScan mutation used by the working prototype."""
    # json.dumps produces a correctly escaped GraphQL string literal.
    path_literal = json.dumps(path)
    query = f"mutation MetadataScan {{ metadataScan(input: {{ paths: [{path_literal}] }}) }}"
    stash_request(plugin_input, query, {})


def save_next_to_video(plugin_input, scene_id, source_url, ext):
    scene_info = scene(plugin_input, scene_id)
    video_path = scene_info["files"][0]["path"]
    video_file = Path(video_path)
    if not video_file.is_file():
        raise RuntimeError(f"Stash 后端无法访问视频文件：{video_path}")
    safe_ext = "ass" if ext.lower() == "ass" else "srt"
    target_file = video_file.with_name(f"{video_file.stem}.zh.{safe_ext}")
    content, _ = fetch_subtitle(source_url)
    target_file.write_bytes(content)
    try:
        # Limit Stash's scan input to the subtitle file just created instead
        # of walking every file in the video's directory.
        scan_path_for_metadata(plugin_input, str(target_file))
        return {"filename": target_file.name, "scanned": True}
    except (HTTPError, URLError, RuntimeError, ValueError) as exc:
        # The file exists at this point, so scanning must remain non-fatal.
        warning = f"字幕已保存，但自动扫描失败：{exc}"
        log(warning)
        return {"filename": target_file.name, "scanned": False, "scan_error": str(exc)}


def main():
    plugin_input = json.load(sys.stdin)
    args = plugin_input.get("args") or {}
    mode = args.get("mode")
    try:
        if mode == "scene_info":
            info = scene(plugin_input, args["scene_id"])
            result = {"keyword": subtitle_name(info), "title": info.get("title") or ""}
        elif mode == "search":
            result = {"items": search(str(args.get("keyword") or ""))}
        elif mode == "preview":
            raw, charset = fetch_subtitle(str(args["url"]))
            # Avoid sending very large files back to the browser.
            result = {"content": raw[:1_000_000].decode(charset, errors="replace"), "truncated": len(raw) > 1_000_000}
        elif mode == "save":
            result = save_next_to_video(plugin_input, args["scene_id"], args["url"], args.get("ext") or "srt")
        else:
            raise RuntimeError("不支持的后端操作")
        print(json.dumps({"output": {"success": True, "result": result}}, ensure_ascii=False))
    except (KeyError, ValueError, HTTPError, URLError, RuntimeError) as exc:
        log(str(exc))
        print(json.dumps({"error": str(exc), "output": {"success": False, "message": str(exc)}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
