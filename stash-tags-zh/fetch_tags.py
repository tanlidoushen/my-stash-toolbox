#!/usr/bin/env python3
"""
stash-tags-zh — 从 Stash GraphQL 拉取汉化标签（v2 格式）

输出:
  tags-v2.json — 标签清单（name / aliases / description / stash_id）

v2 数据 = 带云端 stash_id 的标签（默认只导出有 stash_id 的）。
每个标签与云端 stashdb 标签一一绑定后导出，用于汉化补丁导入、校验与回填。

用法:
  python3 fetch_tags.py --url http://<stash>:9999/graphql
      # 默认：只导出有 stash_id 的标签
  python3 fetch_tags.py --url http://<stash>:9999/graphql --all
      # 导出全部标签（无 stash_id 的不含该字段）
  python3 fetch_tags.py --url http://<stash>:9999/graphql --out tags-v2.json
"""
import argparse
import json
import urllib.request


def gql(url, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def fetch_all_tags(url):
    """分页拉取全部标签（per_page:-1 一次拉全）"""
    query = """
    query AllTags($filter: FindFilterType!) {
      findTags(filter: $filter) {
        count
        tags {
          id name aliases description
          stash_ids { endpoint stash_id }
        }
      }
    }
    """
    result = gql(url, query, {"filter": {"per_page": -1}})
    data = result.get("data", {}).get("findTags", {})
    return data.get("count", 0), data.get("tags", [])


def main():
    parser = argparse.ArgumentParser(description="stash-tags-zh 标签拉取 (v2)")
    parser.add_argument("--url", required=True, help="Stash GraphQL 地址，如 http://<stash>:9999/graphql")
    parser.add_argument("--out", default="tags-v2.json", help="输出文件名（默认 tags-v2.json）")
    parser.add_argument("--all", action="store_true", help="导出全部标签（默认只导出有 stash_id 的）")
    args = parser.parse_args()

    count, tags = fetch_all_tags(args.url)
    print(f"Stash 标签总数: {count}，拉取: {len(tags)}")

    out = []
    n_with_sid = 0
    for t in tags:
        sids = [s["stash_id"] for s in (t.get("stash_ids") or [])]
        if sids:
            n_with_sid += 1
        if not sids and not args.all:
            continue
        item = {
            "name": t["name"],
            "aliases": t.get("aliases") or [],
            "description": t.get("description") or "",
        }
        if sids:
            item["stash_id"] = sids[0] if len(sids) == 1 else sids
        out.append(item)

    out.sort(key=lambda x: x["name"])

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"有 stash_id 的标签: {n_with_sid}")
    print(f"输出: {args.out} ({len(out)} 个标签)")


if __name__ == "__main__":
    main()
