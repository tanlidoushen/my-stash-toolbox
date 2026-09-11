#!/usr/bin/env python3
"""
stash-tags-zh 汉化补丁导入脚本（v2）

读取 tags-v2.json（name/aliases/description/stash_id），导入目标 Stash：

匹配优先级（按序）:
  1. stash_id 精确匹配 → 覆盖（最可靠，云端 id 唯一）
  2. 同名匹配 → 覆盖
  3. 本地英文别名命中对方 name/aliases → 覆盖（英文原名并入 aliases）
  4. 无匹配 → 新建（写入 stash_id）

覆盖内容: name（汉化）/ aliases（合并去重）/ description（本地空则保留对方）/ stash_id（回填）。
v2 数据不含父子层级，不执行层级挂载。

用法:
  python3 import_tags.py --url http://<stash>:9999/graphql --dry-run   # 预览
  python3 import_tags.py --url http://<stash>:9999/graphql --apply     # 实际执行

⚠️ 破坏性操作警告
  --apply 会覆盖目标 Stash 的标签 name/aliases/description 并回填 stash_id，
  不可逆！执行前务必先备份目标 Stash 数据库。先跑 --dry-run 查看影响报告。
"""
import argparse
import json
import sys
import urllib.request

DESTRUCTIVE_BANNER = r"""
╔══════════════════════════════════════════════════════════════════╗
║  ⚠️  破坏性操作警告  ⚠️                                           ║
║                                                                    ║
║  本脚本 --apply 会覆盖目标 Stash 的标签属性（name/aliases/       ║
║  description）并回填 stash_id，操作不可逆！                      ║
║                                                                    ║
║  【执行前必须备份目标 Stash 数据库】                              ║
║   - Stash 设置 → Metadata → Backup Database                       ║
║   或: docker exec <stash容器> cp -r /root/.stash /backup/         ║
║                                                                    ║
║  强烈建议先运行 --dry-run 查看完整影响报告。                      ║
╚══════════════════════════════════════════════════════════════════╝
"""


def gql(url, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def fetch_remote_tags(url):
    """拉取目标实例全部标签（含 stash_ids）"""
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
    return result.get("data", {}).get("findTags", {}).get("tags", [])


def tag_create(url, name, aliases, description, stash_id):
    mutation = """
    mutation CreateTag($input: TagCreateInput!) {
      tagCreate(input: $input) { id }
    }
    """
    inp = {"name": name, "aliases": aliases or [], "description": description or ""}
    if stash_id:
        inp["stash_ids"] = [{"endpoint": "https://stashdb.org/graphql", "stash_id": stash_id}]
    result = gql(url, mutation, {"input": inp})
    return result.get("data", {}).get("tagCreate", {}).get("id")


def tag_update(url, tag_id, name=None, aliases=None, description=None, stash_ids=None):
    mutation = """
    mutation UpdateTag($input: TagUpdateInput!) {
      tagUpdate(input: $input) { id }
    }
    """
    inp = {"id": tag_id}
    if name is not None:
        inp["name"] = name
    if aliases is not None:
        inp["aliases"] = aliases
    if description is not None:
        inp["description"] = description
    if stash_ids is not None:
        inp["stash_ids"] = stash_ids
    result = gql(url, mutation, {"input": inp})
    return result.get("data", {}).get("tagUpdate", {}).get("id")


def load_local(path="tags-v2.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_remote_index(remote_tags):
    """对方索引: stash_id→tag, name→tag, alias→tag"""
    by_sid, by_name, by_alias = {}, {}, {}
    for t in remote_tags:
        by_name[t["name"]] = t
        for s in (t.get("stash_ids") or []):
            by_sid.setdefault(s["stash_id"], t)
        for a in t.get("aliases") or []:
            by_alias.setdefault(a, t)
    return by_sid, by_name, by_alias


def classify(local, remote_tags):
    by_sid, by_name, by_alias = build_remote_index(remote_tags)
    plan = {"sid_match": [], "name_match": [], "alias_match": [], "create": [], "conflict": []}
    covered = set()  # 已安排覆盖的对方标签 id

    for t in local:
        name = t["name"]
        sid = t.get("stash_id")
        # 1. stash_id 精确匹配
        if sid and sid in by_sid and by_sid[sid]["id"] not in covered:
            plan["sid_match"].append((name, by_sid[sid], sid))
            covered.add(by_sid[sid]["id"])
            continue
        # 2. 同名匹配
        if name in by_name and by_name[name]["id"] not in covered:
            plan["name_match"].append((name, by_name[name]))
            covered.add(by_name[name]["id"])
            continue
        # 3. 别名匹配
        matched = []
        for a in t.get("aliases") or []:
            if a in by_name:
                matched.append(by_name[a])
            elif a in by_alias:
                matched.append(by_alias[a])
        matched = [m for m in matched if m["id"] not in covered]
        if len(matched) > 1:
            plan["conflict"].append((name, matched))
        elif matched:
            plan["alias_match"].append((name, matched[0]))
            covered.add(matched[0]["id"])
        else:
            plan["create"].append(t)
    return plan


def main():
    parser = argparse.ArgumentParser(description="stash-tags-zh 汉化补丁导入 (v2)")
    parser.add_argument("--url", required=True, help="目标 Stash GraphQL 地址")
    parser.add_argument("--data", default="tags-v2.json", help="v2 数据文件（默认 tags-v2.json）")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="只预览，不写库")
    group.add_argument("--apply", action="store_true", help="实际执行")
    args = parser.parse_args()

    if args.apply:
        print(DESTRUCTIVE_BANNER)
        confirm = input("确认已在目标 Stash 备份数据库，且理解这是破坏性操作？输入 YES 继续: ")
        if confirm.strip() != "YES":
            print("已取消")
            sys.exit(1)

    local = load_local(args.data)
    print(f"本地(v2)标签: {len(local)} 个")

    remote_tags = fetch_remote_tags(args.url)
    print(f"对方标签: {len(remote_tags)} 个")

    plan = classify(local, remote_tags)
    print(f"\n=== 匹配结果 ===")
    print(f"🔗 stash_id 匹配: {len(plan['sid_match'])}")
    print(f"🈶 同名匹配:     {len(plan['name_match'])}")
    print(f"🔤 别名匹配:     {len(plan['alias_match'])}")
    print(f"➕ 新建:         {len(plan['create'])}")
    print(f"⚠️  冲突:        {len(plan['conflict'])}")

    print("\n--- 覆盖预览（前 20）---")
    for name, remote, *rest in plan["sid_match"][:20]:
        print(f"  [sid] {remote['name']} → {name}")
    for name, remote in plan["name_match"][:20]:
        print(f"  [name] {remote['name']} → {name}")
    for name, remote in plan["alias_match"][:20]:
        print(f"  [alias] {remote['name']} → {name}")

    print("\n--- 新建预览（前 20）---")
    for t in plan["create"][:20]:
        print(f"  {t['name']}")

    if plan["conflict"]:
        print("\n--- 冲突（多个候选，取第一个，人工确认）---")
        for name, matched in plan["conflict"][:10]:
            cands = ", ".join(m["name"] for m in matched)
            print(f"  {name} ↔ {cands}")

    # 保存计划
    with open("import_plan.json", "w", encoding="utf-8") as f:
        json.dump({
            "overwrite": [{"local": name, "remote_id": r["id"], "remote_name": r["name"]}
                          for name, r, *rest in plan["sid_match"]]
                       + [{"local": name, "remote_id": r["id"], "remote_name": r["name"]}
                          for name, r in plan["name_match"]]
                       + [{"local": name, "remote_id": r["id"], "remote_name": r["name"]}
                          for name, r in plan["alias_match"]],
            "create": plan["create"],
            "conflict": [{"name": n, "candidates": [m["name"] for m in ms]}
                         for n, ms in plan["conflict"]],
        }, f, ensure_ascii=False, indent=2)

    if args.apply:
        print("\n=== 开始执行 ===")
        n_ov, n_new = 0, 0

        def do_overwrite(name, remote, sid=None):
            nonlocal n_ov
            t = next(x for x in local if x["name"] == name)
            new_aliases = list(dict.fromkeys(
                ([remote["name"]] if remote["name"] != name else []) +
                (remote.get("aliases") or []) +
                (t.get("aliases") or [])
            ))
            new_description = t.get("description") or remote.get("description") or ""
            # 补 stash_id（目标无则回填）
            have_sids = [{"endpoint": s["endpoint"], "stash_id": s["stash_id"]}
                         for s in (remote.get("stash_ids") or [])]
            if sid and sid not in [s["stash_id"] for s in have_sids]:
                have_sids.append({"endpoint": "https://stashdb.org/graphql", "stash_id": sid})
            tag_update(args.url, remote["id"], name=name, aliases=new_aliases,
                       description=new_description, stash_ids=have_sids)
            n_ov += 1
            print(f"🈶 覆盖: {remote['name']} → {name}")

        for name, remote, sid in plan["sid_match"]:
            do_overwrite(name, remote, sid)
        for name, remote in plan["name_match"]:
            do_overwrite(name, remote, None)
        for name, remote in plan["alias_match"]:
            do_overwrite(name, remote, None)

        for t in plan["create"]:
            new_id = tag_create(args.url, t["name"], t.get("aliases") or [],
                                t.get("description") or "", t.get("stash_id"))
            if new_id:
                n_new += 1
                print(f"➕ 新建: {t['name']} (id={new_id})")

        print(f"\n完成！覆盖 {n_ov}，新建 {n_new}")


if __name__ == "__main__":
    main()
