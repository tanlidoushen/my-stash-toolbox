import asyncio, sys
sys.path.insert(0, "/app")
from config import Config
from stash.client import StashClient

async def main():
    client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)

    # 查 Gallery 详情（用正确的字段）
    for gid in ("5085", "5086"):
        q = '{ findGallery(id: "%s") { id title image_count performers { id name } } }' % gid
        r = await client.post(q, {})
        g = r.get("findGallery") or {}
        print(f"Gallery {gid}: {g.get('title')}")
        print(f"  image_count: {g.get('image_count')}")
        print(f"  performers: {[p.get('name') for p in (g.get('performers') or [])]}")
        print()

    # 查 5571 路径的图片（前5个，看 gallery_ids）
    q2 = '{ findImages(image_filter: { path: { value: "5571", modifier: INCLUDES } }, filter: { per_page: 5 }) { count images { id title gallery_ids path } } }'
    r2 = await client.post(q2, {})
    imgs = r2.get("findImages", {})
    print(f"5571 路径图片总数: {imgs.get('count')}")
    for img in (imgs.get("images") or []):
        print(f"  id={img['id']} gallery_ids={img.get('gallery_ids')} title={img.get('title','')[:40]}")

asyncio.run(main())
