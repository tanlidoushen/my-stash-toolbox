"""删除场景：CloudDrive2 物理删除 → Stash 场景销毁。"""

import logging
import asyncio

from config import Config
from cd2_client import get_cd2_client

logger = logging.getLogger(__name__)


def _stash_path_to_cd2(file_path):
    """将 Stash 中的真实路径转为 CD2 虚拟路径。

    现有脚本统一做法：去掉 <local-mount-prefix> 前缀，
    剩下的就是 CD2 能识别的虚拟路径（保留 /<cloud-path>/ 等挂载前缀）。
    """
    if Config.CD2_STRIP_PREFIX and file_path.startswith(Config.CD2_STRIP_PREFIX):
        return "/" + file_path[len(Config.CD2_STRIP_PREFIX):].lstrip("/")
    return file_path


def _delete_cd2_file(cd2_path):
    """通过 gRPC 调用 CloudDrive2 删除单个文件。返回 (ok, error_msg)。"""
    try:
        data = get_cd2_client().delete_file(cd2_path)
        if data.get("success"):
            return True, None
        return False, data.get("errorMessage", "未知错误")
    except Exception as e:
        return False, str(e)[:150]


async def delete_scene(client, scene_id):
    """删除场景完整流程。

    返回: {
        "scene_id": str,
        "title": str,
        "code": str|None,
        "date": str|None,
        "studio": str|None,
        "performers": str,
        "details": [{"path": str, "cd2_path": str, "ok": bool, "error": str|None}],
        "files_deleted": int,
        "files_failed": int,
        "files_total": int,
        "scene_destroyed": bool,
        "scene_error": str|None,
    }
    """
    from stash import query as Q

    # ── 1. 查场景信息 ──
    data = await client.post(Q.SCENE_FOR_NOTIFICATION, {"id": str(scene_id)})
    if not data:
        return {"error": f"无法查询场景 {scene_id}"}

    scene = data.get("findScene")
    if not scene:
        return {"error": f"未找到场景 {scene_id}"}

    title = scene.get("title") or "(无标题)"
    files = scene.get("files", [])

    # 提取额外元数据
    code = scene.get("code") or None
    date = scene.get("date") or None
    studio_name = None
    studio_id = None
    studio = scene.get("studio")
    if studio:
        studio_name = studio.get("name") or None
        studio_id = studio.get("id") or None
    performer_list = []
    performer_ids = []
    for p in scene.get("performers", []):
        name = p.get("name")
        pid = p.get("id")
        if name:
            performer_list.append(name)
            if pid:
                performer_ids.append(pid)
    performer_str = ", ".join(performer_list) if performer_list else ""
    performer_ids_str = ",".join(performer_ids) if performer_ids else ""

    result = {
        "scene_id": str(scene_id),
        "title": title,
        "code": code,
        "date": date,
        "studio": studio_name,
        "studio_id": studio_id,
        "performers": performer_str,
        "performer_ids": performer_ids_str,
        "files_deleted": 0,
        "files_failed": 0,
        "files_total": len(files),
        "details": [],
        "scene_destroyed": False,
        "scene_error": None,
    }

    # ── 2. 逐文件 CloudDrive2 物理删除 ──
    for f in files:
        stash_path = f.get("path", "")
        cd2_path = _stash_path_to_cd2(stash_path)
        logger.info("  🗑 CloudDrive2 删除: %s", cd2_path)

        ok, err = await asyncio.to_thread(_delete_cd2_file, cd2_path)
        detail = {"path": stash_path, "cd2_path": cd2_path, "ok": ok, "error": err}
        result["details"].append(detail)

        if ok:
            result["files_deleted"] += 1
        else:
            result["files_failed"] += 1
            logger.warning("  ❌ CloudDrive2 删除失败: %s — %s", cd2_path, err)

    # ── 3. Stash 中销毁场景 ──
    logger.info("  🗑 Stash sceneDestroy: %s", scene_id)
    destroy_data = await client.post(Q.SCENE_DESTROY, {"id": str(scene_id)})
    if destroy_data and destroy_data.get("sceneDestroy"):
        result["scene_destroyed"] = True
        logger.info("  ✅ 场景 %s 已销毁", scene_id)
    else:
        result["scene_error"] = "sceneDestroy 返回失败"
        logger.error("  ❌ 场景 %s 销毁失败", scene_id)

    return result
