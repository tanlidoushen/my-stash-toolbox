"""标记同步编排入口：sync_markers_all。

双源标记+集合同步统一入口，在 Non-JAV 刮削流程中调用。
"""
import logging

from config import Config
from scrape.marker_sync_client import TTClient, TPDBClient
from scrape.marker_sync_util import (
    sync_markers, sync_tags, sync_urls, sync_stash_ids,
    sync_groups, sync_groups_tpdb,
)
from stash import scene as scene_mod
from stash import tag as tag_mod

logger = logging.getLogger(__name__)

# 外网代理（与 box.py 一致）
STASHBOX_PROXY = getattr(Config, "STASHBOX_PROXY", "http://<proxy>:7890")
TPDB_ENDPOINT = "https://theporndb.net/graphql"


async def _get_tpdb_api_key(client) -> str:
    """从 Stash 配置中获取 TPDB API key。"""
    data = await client.post("""
        query {
          configuration { general { stashBoxes { endpoint api_key } } }
        }
    """, {})
    if not data:
        return ""
    for b in data.get("configuration", {}).get("general", {}).get("stashBoxes", []):
        ep = b.get("endpoint") or ""
        if "theporndb.net" in ep:
            key = b.get("api_key") or ""
            if key:
                return key
    return ""


async def sync_markers_all(client, scene_id: str, proxy: str = None) -> dict:
    """双源标记+集合同步统一入口。

    Args:
        client: StashClient
        scene_id: 本地场景 ID
        proxy: 外网代理（默认从 STASHBOX_PROXY 读取）

    Returns:
        {tt: bool, tpdb: bool, markers: bool, groups: int}
    """
    result = {"tt": False, "tpdb": False, "markers": False, "groups": 0}
    proxy = proxy or STASHBOX_PROXY

    # 1. 拉场景
    scene = await scene_mod.get_scene_for_marker_sync(client, scene_id)
    if not scene:
        logger.warning("      - ⚠️ 场景 %s 不存在，跳过标记同步", scene_id)
        return result

    stash_ids = scene.get("stash_ids") or []
    markers_changed = False

    # 2. tt 源（stashdb stash_id → get-markers → json-scene）
    stashdb_sid = next(
        (x["stash_id"] for x in stash_ids
         if "stashdb.org" in (x.get("endpoint") or "")),
        None,
    )
    if stashdb_sid:
        logger.info("      - 🔗 [tt] 反查 stashdb_id=%s...", stashdb_sid[:12])
        tt = TTClient(proxy)
        try:
            md = await tt.get_markers(stashdb_sid)
            if md and md.get("scene_id"):
                tt_scene_id = md["scene_id"]
                tt_scene = await tt.get_scene(tt_scene_id)
                if tt_scene:
                    tt_scene["scene_id"] = tt_scene_id
                    # 标记同步
                    changed = await sync_markers(
                        client, scene, tt_scene.get("markers") or [],
                        "[tt]",
                        add_tag=Config.MARKER_SYNC_TT_TAG,
                        add_title=Config.MARKER_SYNC_TT_TITLE,
                        source_tag="[Timestamp]", source_prefix="[TsTrade] ",
                    )
                    markers_changed = markers_changed or changed
                    # 标签/url/stash_id/集合同步
                    await sync_tags(client, scene, tt_scene)
                    await sync_urls(client, scene, tt_scene)
                    await sync_stash_ids(client, scene, tt_scene)
                    await sync_groups(client, scene, tt_scene)
                else:
                    logger.info("      - ⚠️ [tt] json-scene 拉取失败")
            else:
                logger.info("      - ⚠️ [tt] 无对应场景")
        finally:
            await tt.close()
    else:
        logger.info("      - ℹ️  场景无 stashdb.org 的 stash_id，跳过 tt 源")

    result["tt"] = markers_changed

    # 3. 刷新场景快照（tt 可能刚建了标记）
    scene = await scene_mod.get_scene_for_marker_sync(client, scene_id)
    if not scene:
        return result
    stash_ids = scene.get("stash_ids") or []

    # 4. TPDB 源（theporndb stash_id → api.theporndb.net）
    tpdb_sid = next(
        (x["stash_id"] for x in stash_ids
         if "theporndb.net" in (x.get("endpoint") or "")),
        None,
    )
    if tpdb_sid:
        tpdb_key = await _get_tpdb_api_key(client)
        if tpdb_key:
            tpdb = TPDBClient(tpdb_key, proxy)
            try:
                tpdb_scene = await tpdb.get_scene(tpdb_sid)
                if tpdb_scene:
                    logger.info("      - 🔗 [TPDB] 场景: %s", tpdb_scene.get("url") or tpdb_scene.get("title"))
                    # 标记补缺
                    changed = await sync_markers(
                        client, scene, tpdb_scene.get("markers") or [],
                        "[TPDB]",
                        add_tag=Config.MARKER_SYNC_TPDB_TAG,
                        add_title=Config.MARKER_SYNC_TPDB_TITLE,
                        source_tag="[TPDBMarker]", source_prefix="[TPDBMarker] ",
                        skip_existing=True,
                    )
                    markers_changed = markers_changed or changed
                    # 集合同步（补充 tt 缺失的 image/back_image）
                    await sync_groups_tpdb(client, scene, tpdb_scene)
                else:
                    logger.info("      - ⚠️ [TPDB] 场景拉取失败")
            finally:
                await tpdb.close()
        else:
            logger.info("      - ⚠️ [TPDB] 本地未配置 theporndb stash-box 实例（无 API key）")
    else:
        logger.info("      - ℹ️  场景无 theporndb.net 的 stash_id，跳过 TPDB 源")

    result["tpdb"] = markers_changed and not result["tt"]  # TPDB 自己贡献的变更
    result["markers"] = markers_changed

    # 5. 标记有变更 → 触发 marker 产物生成
    if markers_changed:
        job = await scene_mod.generate_marker_previews(client, scene_id)
        logger.info("      - 🎬 标记有变更，已触发 Stash 生成 marker 产物（job %s）："
                     "markers 视频流 + 动图 preview + 截图 screenshot", job)

    logger.info("      - ✅ 标记同步完成: tt=%s tpdb=%s markers=%s",
                result["tt"], result["tpdb"], result["markers"])
    return result