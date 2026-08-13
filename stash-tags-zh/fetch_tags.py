#!/usr/bin/env python3
"""
stash-tags-zh — 从 Stash GraphQL 拉取中文汉化标签层级分析

输出:
  parents.json   — 有下级标签的中文上级标签（含其下级标签列表）
  children.json  — 有上级标签的中文下级标签（含其上级标签）
孤儿标签（无父无子）不处理。

用法:
  python3 fetch_tags.py --url http://<stash>:9999/graphql
"""
import argparse
import json
import re
import sys
import urllib.request

CN_RE = re.compile(r"[\u4e00-\u9fff]")


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
          parents { id name }
          children { id name }
        }
      }
    }
    """
    result = gql(url, query, {"filter": {"per_page": -1}})
    data = result.get("data", {}).get("findTags", {})
    return data.get("count", 0), data.get("tags", [])


def is_cn(name):
    return bool(CN_RE.search(name or ""))


def main():
    parser = argparse.ArgumentParser(description="stash-tags-zh 标签拉取")
    parser.add_argument("--url", required=True, help="Stash GraphQL 地址，如 http://<stash>:9999/graphql")
    args = parser.parse_args()

    count, tags = fetch_all_tags(args.url)
    print(f"Stash 标签总数: {count}，拉取: {len(tags)}")

    cn_tags = [t for t in tags if is_cn(t["name"])]
    print(f"中文标签: {len(cn_tags)}")

    # 有下级标签的中文上级标签（不含本地 id，便于分享）
    parents = [
        {
            "name": t["name"],
            "aliases": t.get("aliases") or [],
            "description": t.get("description") or "",
            "children_count": len(t["children"]),
            "children": [{"name": c["name"]} for c in t["children"]],
        }
        for t in cn_tags
        if t["children"]
    ]
    parents.sort(key=lambda x: -x["children_count"])

    # 有上级标签的中文下级标签（不含本地 id，便于分享）
    children = [
        {
            "name": t["name"],
            "aliases": t.get("aliases") or [],
            "description": t.get("description") or "",
            "parents_count": len(t["parents"]),
            "parents": [{"name": p["name"]} for p in t["parents"]],
        }
        for t in cn_tags
        if t["parents"]
    ]
    children.sort(key=lambda x: -x["parents_count"])

    with open("parents.json", "w", encoding="utf-8") as f:
        json.dump(parents, f, ensure_ascii=False, indent=2)
    with open("children.json", "w", encoding="utf-8") as f:
        json.dump(children, f, ensure_ascii=False, indent=2)

    print(f"输出: parents.json ({len(parents)} 个上级标签) / children.json ({len(children)} 个下级标签)")


if __name__ == "__main__":
    main()