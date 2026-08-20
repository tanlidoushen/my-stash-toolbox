"""场景操作：查找、查询、更新、stash_id 管理。"""

import logging

from stash import query as Q

logger = logging.getLogger(__name__)


async def find_scenes_by_path(client, path):
    """按文件路径查找场景 ID 列表。"""
    variables = {
        "filter": {"path": {"value": path, "modifier": "EQUALS"}}
    }
    data = await client.post(Q.FIND_SCENES_BY_PATH, variables)
    if not data:
        return []
    scenes = data.get("findScenes", {}).get("scenes", [])
    logger.info("      - ✅ 找到 %d 个场景", len(scenes))
    return [s["id"] for s in scenes]


async def get_scene_info(client, scene_id):
    """获取场景基本信息。"""
    data = await client.post(Q.SCENE_FOR_NOTIFICATION, {"id": str(scene_id)})
    if data:
        return data.get("findScene")
    return None


async def get_scene_stash_id(client, scene_id, stash_box_index=0):
    """查询场景的 stash_id。返回 stash_id 或 None。"""
    endpoint = await client.get_endpoint(stash_box_index)
    data = await client.post(Q.FIND_SCENE_STASH_IDS, {"id": str(scene_id)})
    if data is None:
        return None
    scene = data.get("findScene")
    if not scene:
        return None
    for si in scene.get("stash_ids", []):
        if si["endpoint"] == endpoint:
            return si["stash_id"]
    return None



async def add_scene_stash_id(client, scene_id, stash_id, stash_box_index=0):
    """给场景添加 stash_id。"""
    info = await get_scene_info(client, scene_id)
    if not info:
        logger.warning("添加 stash_id 失败: 场景 %s", scene_id)
        return False
    endpoint = await client.get_endpoint(stash_box_index)
    stash_ids = info.get("stash_ids", [])
    stash_ids.append({"endpoint": endpoint, "stash_id": stash_id})
    result = await update_scene(client, {"id": str(scene_id), "stash_ids": stash_ids})
    if result:
        logger.info("已为场景 %s 添加 stash_id=%s", scene_id, stash_id)
        return True
    logger.warning("添加 stash_id 失败: 场景 %s", scene_id)
    return False


async def update_scene(client, input_data):
    """更新场景元数据。返回是否成功。"""
    data = await client.post(Q.SCENE_UPDATE, {"input": input_data})
    if data and data.get("sceneUpdate"):
        updated = data["sceneUpdate"]
        logger.info(
            "         - 更新成功 | 标题=%s | 番号=%s | 日期=%s | 片商=%s | 演员=%d | 标签=%d",
            updated.get("title") or "",
            updated.get("code") or "",
            updated.get("date") or "",
            (updated.get("studio") or {}).get("name", ""),
            len(updated.get("performers", [])),
            len(updated.get("tags", [])),
        )
        return True
    logger.error("         - 更新失败 | 场景=%s", input_data.get("id"))
    return False


# ── 标记（markers）──

async def get_scene_for_marker_sync(client, scene_id):
    """获取场景全量数据（含 markers/tags/stash_ids/groups/urls）。"""
    data = await client.post(Q.SCENE_FOR_MARKER_SYNC, {"id": str(scene_id)})
    if data:
        return data.get("findScene")
    return None


async def create_scene_marker(client, scene_id, seconds, primary_tag_id, title, tag_ids=None):
    """创建场景标记。返回 marker dict 或 None。"""
    inp = {"scene_id": str(scene_id), "seconds": seconds,
           "primary_tag_id": primary_tag_id, "title": title}
    if tag_ids:
        inp["tag_ids"] = tag_ids
    data = await client.post(Q.SCENE_MARKER_CREATE, {"input": inp})
    if data:
        return data.get("sceneMarkerCreate")
    return None


async def update_scene_marker(client, marker_id, seconds, primary_tag_id, title, tag_ids=None):
    """更新场景标记。返回 marker dict 或 None。"""
    inp = {"id": marker_id, "seconds": seconds,
           "primary_tag_id": primary_tag_id, "title": title}
    if tag_ids:
        inp["tag_ids"] = tag_ids
    data = await client.post(Q.SCENE_MARKER_UPDATE, {"input": inp})
    if data:
        return data.get("sceneMarkerUpdate")
    return None


async def generate_marker_previews(client, scene_id):
    """触发 Stash 生成 marker 三件套（视频流/动图/截图）。"""
    inp = {
        "sceneIDs": [str(scene_id)],
        "markers": True,
        "markerImagePreviews": True,
        "markerScreenshots": True,
        "overwrite": False,
    }
    data = await client.post(Q.GENERATE_MARKERS, {"input": inp})
    return data.get("metadataGenerate") if data else None


# ── 集合（Group）──

async def find_group_by_url(client, url: str = "", name: str = None):
    """按 url 查找本地 Group；url 未命中时按名称回退。返回 group_id 或 None。"""
    data = await client.post(Q.FIND_GROUPS, {"filter": {"per_page": -1}})
    if not data:
        return None
    groups = data.get("findGroups", {}).get("groups", [])
    if url:
        target = url.lower()
        for g in groups:
            if any(u.lower() == target for u in (g.get("urls") or [])):
                return g["id"]
    if name:
        for g in groups:
            if (g.get("name") or "").lower() == name.lower():
                return g["id"]
    return None


async def create_group(client, input_data: dict):
    """创建 Group。返回 group_id 或 None。"""
    data = await client.post(Q.GROUP_CREATE, {"input": input_data})
    if data:
        g = data.get("groupCreate")
        if g:
            return g["id"]
    return None


async def update_group(client, input_data: dict):
    """更新 Group。返回是否成功。"""
    data = await client.post(Q.GROUP_UPDATE, {"input": input_data})
    return data is not None and data.get("groupUpdate") is not None


async def find_group(client, group_id: str):
    """查询 Group 详情。返回 dict 或 None。"""
    data = await client.post(Q.FIND_GROUP, {"id": group_id})
    if data:
        return data.get("findGroup")
    return None


async def find_or_create_studio_by_name(client, name: str):
    """按名称查找工作室，不存在则创建。返回 studio_id 或 None。"""
    from stash import query as Q
    data = await client.post(Q.FIND_STUDIOS, {
        "filter": {"per_page": 1},
        "studio_filter": {"name": {"value": name, "modifier": "EQUALS"}},
    })
    if data:
        studios = data.get("findStudios", {}).get("studios", [])
        if studios:
            return studios[0]["id"]
    data = await client.post(Q.STUDIO_CREATE, {"input": {"name": name}})
    if data:
        s = data.get("studioCreate")
        if s:
            return s["id"]
    return None