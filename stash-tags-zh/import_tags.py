#!/usr/bin/env python3
"""
stash-tags-zh 汉化补丁导入脚本

把本地中文标签体系（parents.json / children.json）作为汉化补丁导入目标 Stash：
- 对方英文标签匹配上 → 覆盖为中文（name/description 汉化，英文原名并入 aliases）
- 已存在中文标签 → 跳过
- 无匹配 → 新建

用法:
  python3 import_tags.py --url http://<stash>:9999/graphql --dry-run   # 预览
  python3 import_tags.py --url http://<stash>:9999/graphql --apply     # 实际执行

⚠️ 破坏性操作警告
  --apply 会覆盖目标 Stash 的标签 name/aliases/description 并修改父子层级，
  不可逆！执行前务必先备份目标 Stash 数据库（stash/metadata 备份）。
  先跑 --dry-run 查看完整影响报告再决定是否执行。
"""
import argparse
import json
import re
import sys
import urllib.request

DESTRUCTIVE_BANNER = r"""
╔══════════════════════════════════════════════════════════════════╗
║  ⚠️  破坏性操作警告  ⚠️                                           ║
║                                                                    ║
║  本脚本 --apply 会覆盖目标 Stash 的标签属性（name/aliases/       ║
║  description）并修改父子层级关系，操作不可逆！                    ║
║                                                                    ║
║  【执行前必须备份目标 Stash 数据库】                              ║
║   - Stash 设置 → Metadata → Backup Database                       ║
║   或: docker exec <stash容器> cp -r /root/.stash /backup/         ║
║                                                                    ║
║  强烈建议先运行 --dry-run 查看完整影响报告。                      ║
╚══════════════════════════════════════════════════════════════════╝
"""

CN_RE = re.compile(r"[\u4e00-\u9fff]")


def gql(url, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def fetch_remote_tags(url):
    """拉取对方实例全部标签"""
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
    return result.get("data", {}).get("findTags", {}).get("tags", [])


def tag_create(url, name, aliases, description):
    mutation = """
    mutation CreateTag($input: TagCreateInput!) {
      tagCreate(input: $input) { id }
    }
    """
    result = gql(url, mutation, {"input": {
        "name": name, "aliases": aliases or [], "description": description or ""}})
    return result.get("data", {}).get("tagCreate", {}).get("id")


def tag_update(url, tag_id, name=None, aliases=None, description=None, parent_ids=None):
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
    if parent_ids is not None:
        inp["parent_ids"] = parent_ids
    result = gql(url, mutation, {"input": inp})
    return result.get("data", {}).get("tagUpdate", {}).get("id")


def load_local():
    """读取本地 parents.json / children.json，返回 {中文名: {data}} 全量"""
    tags = {}
    parent_count = 0
    for path in ("parents.json", "children.json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if path == "parents.json":
            parent_count = len(data)
        for t in data:
            tags[t["name"]] = t
    return tags, parent_count


def build_remote_index(remote_tags):
    """构建对方索引: name→tag, alias→tag"""
    by_name = {}
    by_alias = {}
    for t in remote_tags:
        by_name[t["name"]] = t
        for a in t.get("aliases") or []:
            by_alias.setdefault(a, t)
    return by_name, by_alias


def classify(local, remote_tags):
    """对每个本地标签分类: skip / overwrite / create
    - skip: 对方已有完全一致的中文标签（name/aliases/description 全同）
    - overwrite: 同名但别名/描述不一致，或别名匹配到英文标签 → 覆盖汉化
    - create: 无匹配 → 新建
    """
    by_name, by_alias = build_remote_index(remote_tags)
    plan = {"skip": [], "overwrite": [], "create": [], "conflict": []}
    covered_ids = set()  # 已安排覆盖的对方标签 id（去重）

    def same_tag(remote, t):
        """对方标签与本地标签是否完全一致（aliases 集合 + description）"""
        local_aliases = set(t.get("aliases") or [])
        remote_aliases = set(remote.get("aliases") or [])
        return local_aliases == remote_aliases and (t.get("description") or "") == (remote.get("description") or "")

    for name, t in local.items():
        aliases = t.get("aliases") or []
        remote = by_name.get(name)
        if remote:
            if same_tag(remote, t):
                plan["skip"].append((name, "完全一致"))
            else:
                plan["overwrite"].append((name, remote, "同名但别名/描述不一致"))
                covered_ids.add(remote["id"])
            continue
        # 我的中文名已在对方别名 → 对方半汉化，覆盖 name 为中文
        if name in by_alias and by_alias[name]["id"] not in covered_ids:
            plan["overwrite"].append((name, by_alias[name], "中文名在对方别名，补覆盖"))
            covered_ids.add(by_alias[name]["id"])
            continue
        # 我的英文别名匹配对方 name/aliases
        matched = []
        for a in aliases:
            if a in by_name:
                matched.append(by_name[a])
            elif a in by_alias:
                matched.append(by_alias[a])
        matched = [m for m in matched if m["id"] not in covered_ids]
        if len(matched) > 1:
            plan["conflict"].append((name, matched))
        elif matched:
            plan["overwrite"].append((name, matched[0], "英文别名匹配"))
            covered_ids.add(matched[0]["id"])
        else:
            plan["create"].append((name, t))
    return plan, by_name


def main():
    parser = argparse.ArgumentParser(description="stash-tags-zh 汉化补丁导入")
    parser.add_argument("--url", required=True, help="目标 Stash GraphQL 地址")
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

    local, parent_count = load_local()
    print(f"本地标签: {len(local)} 个（父 {parent_count} + 子 {len(local) - parent_count}）")

    remote_tags = fetch_remote_tags(args.url)
    print(f"对方标签: {len(remote_tags)} 个")

    plan, by_name = classify(local, remote_tags)
    by_name_for_map = by_name  # 供 --apply 阶段做 skip 标签的 id 映射
    print(f"\n=== 匹配结果 ===")
    print(f"⏭️  跳过(已存在):   {len(plan['skip'])}")
    print(f"🈶 覆盖(汉化):     {len(plan['overwrite'])}")
    print(f"➕ 新建:           {len(plan['create'])}")
    print(f"⚠️  别名冲突:      {len(plan['conflict'])}")

    print("\n--- 覆盖预览（前 20）---")
    for name, remote, reason in plan["overwrite"][:20]:
        print(f"  {remote['name']} → {name}  [{reason}]")

    print("\n--- 新建预览（前 20）---")
    for name, t in plan["create"][:20]:
        print(f"  {name}")

    if plan["conflict"]:
        print("\n--- 冲突（多个候选，取第一个，人工确认）---")
        for name, matched in plan["conflict"][:10]:
            cands = ", ".join(m["name"] for m in matched)
            print(f"  {name} ↔ {cands}")

    # 保存计划供 --apply 使用
    with open("import_plan.json", "w", encoding="utf-8") as f:
        json.dump({
            "overwrite": [{"local": n, "remote_id": r["id"], "remote_name": r["name"], "reason": reason}
                          for n, r, reason in plan["overwrite"]],
            "create": [{"name": n, "aliases": t.get("aliases") or [],
                        "description": t.get("description") or ""}
                       for n, t in plan["create"]],
            "conflict": [{"name": n, "candidates": [m["name"] for m in ms]}
                         for n, ms in plan["conflict"]],
        }, f, ensure_ascii=False, indent=2)

    if args.apply:
        print("\n=== 开始执行 ===")
        id_map = {}  # 本地中文名 → 对方最终 id

        # 1. 覆盖匹配到的标签（先父后子由数据顺序保证：parents.json 在前）
        for name, remote, reason in plan["overwrite"]:
            t = local[name]
            new_aliases = list(dict.fromkeys(
                ([remote["name"]] if remote["name"] != name else []) +
                (remote.get("aliases") or []) +
                (t.get("aliases") or [])
            ))
            # 本地 description 为空 → 保留对方原描述（不覆盖为空）
            new_description = t.get("description") or remote.get("description") or ""
            tag_update(args.url, remote["id"],
                       name=name, aliases=new_aliases,
                       description=new_description)
            id_map[name] = remote["id"]
            print(f"🈶 覆盖: {remote['name']} → {name}  [{reason}]")

        # 2. 新建
        for name, t in plan["create"]:
            new_id = tag_create(args.url, name, t.get("aliases") or [],
                                t.get("description") or "")
            if new_id:
                id_map[name] = new_id
                print(f"➕ 新建: {name} (id={new_id})")

        # 3. 跳过/冲突的也纳入 id_map（用于层级挂载）
        for name, _ in plan["skip"]:
            if name in by_name_for_map:
                id_map[name] = by_name_for_map[name]
        for name, matched in plan["conflict"]:
            if matched:
                id_map[name] = matched[0]["id"]

        # 4. 建立层级：子标签挂到父标签下（用 children.json 的 parents 信息）
        with open("children.json", encoding="utf-8") as f:
            children_data = json.load(f)
        hierarchy_count = 0
        for child in children_data:
            cname = child["name"]
            cid = id_map.get(cname)
            if not cid:
                continue
            pids = []
            for p in child.get("parents", []):
                pid = id_map.get(p["name"])
                if pid and pid != cid:
                    pids.append(pid)
            if pids:
                tag_update(args.url, cid, parent_ids=pids)
                hierarchy_count += 1
                print(f"🔗 挂层级: {cname} → {len(pids)} 个父")
        print(f"\n完成！覆盖 {len(plan['overwrite'])}，新建 {len(plan['create'])}，挂层级 {hierarchy_count} 个")


if __name__ == "__main__":
    main()