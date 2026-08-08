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
