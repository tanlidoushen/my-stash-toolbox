import asyncio, sys
sys.path.insert(0, "/app")
from config import Config
from stash.client import StashClient
async def main():
    c = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)
    for gid in ("5085", "5086"):
        q = '{ findGallery(id: "%s") { id title image_count } }' % gid
        r = await c.post(q, {})
        g = r.get("findGallery") or {}
        print(f"Gallery {gid}: {g.get('title')} | images={g.get('image_count')}")
asyncio.run(main())
