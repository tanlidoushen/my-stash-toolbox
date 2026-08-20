import sys
sys.path.insert(0, "/app")
from config import Config
from stash.client import StashClient

client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)

# 查 addGalleryImages 和 findJob 的 Mutation 签名
q = '{ __type(name: "Mutation") { fields { name args { name type { name kind ofType { name kind ofType { name } } } } } } }'
r = client.gql(q)
for f in (r.get("__type") or {}).get("fields") or []:
    name = f.get("name") or ""
    if name in ("addGalleryImages", "findJob", "galleryCreate"):
        args = []
        for a in f.get("args") or []:
            t = a["type"]
            tname = t.get("name") or ""
            if not tname:
                inner = t.get("ofType") or {}
                tname = inner.get("name") or ""
                if not tname:
                    inner2 = inner.get("ofType") or {}
                    tname = inner2.get("name") or "??"
            args.append(f'{a["name"]}: {tname}')
        print(f"  {name}({", ".join(args)})")
