"""软删场景：仅从 Stash 移除记录（sceneDestroy 不删文件），TG 发确认按钮。

流程（Yamby 删除联动）：
  Yamby 删除 → SJP → POST /api/delete_scene → 软删 + TG 按钮消息
  → 用户点「✅ 确定删除」→ CD2 物理删文件 + 通知
  → 用户点「♻️ 恢复」→ 快速扫描原路径重新入库 + sceneUpdate 回写元数据 + 通知

⚠️ 软删前必须完整备份场景元数据（含截图 base64）：
    sceneDestroy 删除场景记录后，刮削元数据（标题/番号/演员/标签/海报）随之消失；
    metadataScan 重建的场景只有文件名解析的裸数据。恢复 = 重建 + 回写备份。

pending 记录落盘 /app/data/pending_deletes.json（容器重启不丢，按钮仍可操作）。
"""

import asyncio
import base64
import json
import logging
import os
import threading
import time

import httpx

from config import Config
from stash import query as Q

logger = logging.getLogger(__name__)

# ── 查询 ──────────────────────────────────────────────

# 完整元数据备份查询（软删前用；SCENE_FOR_NOTIFICATION 字段不够全）
SCENE_BACKUP = """
query BackupScene($id: ID!) {
  findScene(id: $id) {
    id title details date director code rating100 organized o_counter
    url urls
    files { path size duration }
    paths { screenshot }
    tags { id name }
    performers { id name gender }
    studio { id name }
    stash_ids { endpoint stash_id }
  }
}
"""

SCENE_UPDATE = """
mutation UpdateScene($input: SceneUpdateInput!) {
  sceneUpdate(input: $input) { id }
}
"""

# ── pending 状态存储（JSON 文件 + 线程锁） ──────────────

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PENDING_FILE = os.path.join(_DATA_DIR, "pending_deletes.json")
_pending_lock = threading.Lock()


def _load_pending():
    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_pending(data):
    os.makedirs(_DATA_DIR, exist_ok=True)
    tmp = PENDING_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PENDING_FILE)


def get_pending(scene_id):
    with _pending_lock:
        return _load_pending().get(str(scene_id))


def set_pending(scene_id, record):
    with _pending_lock:
        data = _load_pending()
        data[str(scene_id)] = record
        _save_pending(data)


def pop_pending(scene_id):
    with _pending_lock:
        data = _load_pending()
        rec = data.pop(str(scene_id), None)
        if rec is not None:
            _save_pending(data)
        return rec


# ── TG 确认按钮消息（httpx 裸调，不依赖 bot 实例） ──────

async def _send_tg_confirm(record):
    """发送带「确定删除/恢复」按钮的图片消息（2026-08-17 重构：统一 sender + build_scene_card）。

    复用统一场景卡片（show_details=False 精简版）+ 统一发送层（send_html）。
    """
    chat_id = Config.TG_CHAT_ID
    if not chat_id:
        logger.warning("TG 未配置，无法发送软删确认按钮 scene=%s", record["scene_id"])
        return False

    from notify.sender import send_html
    from notify.builder import build_scene_card

    # record → scene 兼容结构（build_scene_card 需要 performers 数组）
    performers = []
    for a in record.get("female_actors") or []:
        performers.append({"id": a.get("id"), "name": a.get("name", ""), "gender": "FEMALE"})
    for a in record.get("male_actors") or []:
        performers.append({"id": a.get("id"), "name": a.get("name", ""), "gender": "MALE"})
    scene = {
        "id": record.get("scene_id"),
        "title": record.get("title"),
        "code": record.get("code"),
        "date": record.get("date"),
        "performers": performers,
        "studio": None,
        "files": [],
        "tags": [],
        "details": None,
    }

    base = Config.STASH_BASE_URL.rstrip("/")
    extra_lines = [
        "📁 <b>文件:</b> %d 个" % len(record.get("paths", [])),
        "\n❓ <b>是否物理删除文件？</b>",
        "· ✅ 确定删除 → CloudDrive2 物理删除（不可恢复）",
        "· ♻️ 恢复 → 快速扫描重新入库（元数据自动还原）",
    ]
    caption = await build_scene_card(
        scene, False, None, base,
        title_prefix="🗑️ <b>场景已从 Stash 移除</b>\n📁 文件仍在 CloudDrive2，可恢复或删除",
        show_details=False,
        extra_lines=extra_lines,
    )

    reply_markup = {
        "inline_keyboard": [[
            {"text": "✅ 确定删除", "callback_data": "sdel_confirm_%s" % record["scene_id"]},
            {"text": "♻️ 恢复", "callback_data": "sdel_restore_%s" % record["scene_id"]},
        ]]
    }

    # 封面 base64 → bytes（无封面则纯文本）
    cover_b64 = (record.get("meta") or {}).get("cover_b64")
    img_data = None
    if cover_b64:
        try:
            img_data = base64.b64decode(cover_b64.split(",", 1)[1])
        except Exception as e:
            logger.warning("封面 base64 解码失败，改纯文本: %s", e)

    ok = await send_html(chat_id, caption, bot=None, img_data=img_data,
                         reply_markup=reply_markup, filename="cover.jpg")
    if ok:
        logger.info("软删确认消息已发送 scene=%s (photo=%s)", record["scene_id"], bool(img_data))
    return ok


# ── 元数据备份 / 回写 ──────────────────────────────────

async def _backup_cover_b64(scene):
    """下载场景截图转 base64（软删后旧 screenshot URL 会 404，必须先备份）。"""
    ss_url = (scene.get("paths") or {}).get("screenshot")
    if not ss_url:
        return None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as c:
            r = await c.get(ss_url)
        if r.status_code != 200:
            logger.warning("截图下载失败 HTTP %s scene=%s", r.status_code, scene.get("id"))
            return None
        ctype = r.headers.get("content-type", "").split(";")[0].lower()
        if not ctype.startswith("image/"):
            logger.warning("截图非图片 content-type=%s，跳过备份", ctype)
            return None
        return "data:%s;base64,%s" % (ctype, base64.b64encode(r.content).decode())
    except Exception as e:
        logger.warning("截图备份异常 scene=%s: %s", scene.get("id"), e)
        return None


def _build_meta(scene, cover_b64):
    """从场景提取可回写的元数据（实体 ids 在软删后仍有效）。"""
    return {
        "title": scene.get("title"),
        "details": scene.get("details"),
        "date": scene.get("date"),
        "director": scene.get("director"),
        "code": scene.get("code"),
        "rating100": scene.get("rating100"),
        "organized": scene.get("organized"),
        "o_counter": scene.get("o_counter"),
        "url": scene.get("url"),
        "urls": scene.get("urls") or [],
        "studio_id": (scene.get("studio") or {}).get("id"),
        "performer_ids": [p["id"] for p in (scene.get("performers") or []) if p.get("id")],
        "tag_ids": [t["id"] for t in (scene.get("tags") or []) if t.get("id")],
        "stash_ids": scene.get("stash_ids") or [],
        "cover_b64": cover_b64,
    }


async def _restore_meta(client, scene_id, meta):
    """sceneUpdate 回写备份元数据（剔除空值；实体 ids 仍有效）。"""
    if not meta:
        return False
    input_data = {"id": str(scene_id)}
    for k in ("title", "details", "date", "director", "code",
              "rating100", "organized", "o_counter"):
        v = meta.get(k)
        if v is not None and v != "":
            input_data[k] = v
    if meta.get("url"):
        input_data["url"] = meta["url"]
    if meta.get("urls"):
        input_data["urls"] = meta["urls"]
    if meta.get("studio_id"):
        input_data["studio_id"] = meta["studio_id"]
    if meta.get("performer_ids"):
        input_data["performer_ids"] = meta["performer_ids"]
    if meta.get("tag_ids"):
        input_data["tag_ids"] = meta["tag_ids"]
    if meta.get("stash_ids"):
        input_data["stash_ids"] = meta["stash_ids"]
    if meta.get("cover_b64"):
        input_data["cover_image"] = meta["cover_b64"]
    if len(input_data) <= 1:
        return False
    data = await client.post(SCENE_UPDATE, {"input": input_data})
    return bool(data and data.get("sceneUpdate"))


async def _wait_scene_by_path(client, stash_path, timeout=120, interval=3):
    """恢复扫描后轮询按路径查新场景，返回新 scene id（超时 None）。"""
    query = """
    query FindByPath($value: String!) {
      findScenes(scene_filter: { path: { value: $value, modifier: EQUALS } }) {
        count scenes { id }
      }
    }
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            data = await client.post(query, {"value": stash_path})
            scenes = ((data or {}).get("findScenes") or {}).get("scenes") or []
            if scenes:
                return scenes[0]["id"]
        except Exception as e:
            logger.warning("轮询查场景异常: %s", e)
        await asyncio.sleep(interval)
    return None


# ── 主流程 ──────────────────────────────────────────────

async def soft_delete_scene(client, scene_id):
    """软删：完整备份 → sceneDestroy（不删文件）→ 存 pending → TG 确认按钮。

    返回 {"status": "ok", ...} 或 {"error": ...}
    """
    scene_id = str(scene_id)
    data = await client.post(SCENE_BACKUP, {"id": scene_id})
    if not data or not data.get("findScene"):
        return {"error": "未找到场景 %s" % scene_id}
    scene = data["findScene"]

    # 软删前先取路径 + 备份元数据（Stash 记录没了之后就拿不到了）
    paths = [f.get("path", "") for f in (scene.get("files") or []) if f.get("path")]
    from stash.delete import _stash_path_to_cd2
    cd2_paths = [_stash_path_to_cd2(p) for p in paths]
    cover_b64 = await _backup_cover_b64(scene)
    meta = _build_meta(scene, cover_b64)

    # Stash 前端删：SCENE_DESTROY 不传 delete_file → 仅移除记录，不物理删
    destroy = await client.post(Q.SCENE_DESTROY, {"id": scene_id})
    if not destroy or not destroy.get("sceneDestroy"):
        return {"error": "sceneDestroy 失败 scene=%s" % scene_id}

    female_actors = [
        {"id": p.get("id"), "name": p.get("name", "")} for p in (scene.get("performers") or [])
        if p.get("name") and (p.get("gender") or "").upper() != "MALE"
    ]
    male_actors = [
        {"id": p.get("id"), "name": p.get("name", "")} for p in (scene.get("performers") or [])
        if p.get("name") and (p.get("gender") or "").upper() == "MALE"
    ]
    record = {
        "scene_id": scene_id,
        "title": scene.get("title") or "",
        "code": scene.get("code") or "",
        "date": scene.get("date") or "",
        "performers": ", ".join(a["name"] for a in female_actors + male_actors),
        "female_actors": female_actors,
        "male_actors": male_actors,
        "paths": paths,
        "cd2_paths": cd2_paths,
        "meta": meta,
        "deleted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "pending",
    }
    set_pending(scene_id, record)

    tg_ok = await _send_tg_confirm(record)
    return {
        "status": "ok",
        "scene_id": scene_id,
        "title": record["title"],
        "file_count": len(paths),
        "tg_notified": tg_ok,
    }


async def confirm_delete_files(scene_id):
    """TG「✅ 确定删除」：CD2 物理删文件（+ sceneDestroy 容错）。

    返回 dict：files_failed 为空 = 全部成功。
    """
    scene_id = str(scene_id)
    record = get_pending(scene_id)
    if not record:
        return {"error": "没有待确认的软删记录 scene=%s（可能已处理）" % scene_id}

    from stash.delete import _delete_cd2_file

    deleted, failed = 0, []
    for cd2_path in record.get("cd2_paths", []):
        logger.info("  🗑 CD2 删除: %s", cd2_path)
        ok, err = await asyncio.to_thread(_delete_cd2_file, cd2_path)
        if ok:
            deleted += 1
        else:
            failed.append({"path": cd2_path, "error": err})

    # 容错：Stash 记录若还在（罕见），再销毁一次
    from stash.client import StashClient
    try:
        client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)
        await client.post(Q.SCENE_DESTROY, {"id": scene_id})
    except Exception as e:
        logger.warning("sceneDestroy 容错调用异常（记录可能已删）: %s", e)

    return {
        "scene_id": scene_id,
        "title": record.get("title", ""),
        "files_deleted": deleted,
        "files_failed": failed,
    }


async def restore_scene(scene_id):
    """TG「♻️ 恢复」：快速扫描原路径重新入库 + sceneUpdate 回写元数据。"""
    scene_id = str(scene_id)
    record = get_pending(scene_id)
    if not record:
        return {"error": "没有待确认的软删记录 scene=%s（可能已处理）" % scene_id}

    from stash.client import StashClient
    from stash.scanner import scan_simple

    paths = record.get("paths", [])
    if not paths:
        return {"error": "软删记录无文件路径，无法恢复 scene=%s" % scene_id}

    client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)
    job_id = await scan_simple(client, paths)
    if job_id is None:
        return {"error": "恢复扫描提交失败 scene=%s" % scene_id}

    # 等新场景重建，回写备份元数据
    new_scene_id = await _wait_scene_by_path(client, paths[0])
    meta_restored = False
    if new_scene_id:
        meta_restored = await _restore_meta(client, new_scene_id, record.get("meta"))
        logger.info("恢复 scene=%s → 新场景 %s (元数据回写=%s)",
                    scene_id, new_scene_id, meta_restored)
        # 刷新校验码库：stash_scene_id 对应新场景（ed2k 内容指纹幂等命中，秒级）
        try:
            if Config.ENABLE_CHECKSUM:
                from stash.checksum import collect_checksums
                await collect_checksums(client, new_scene_id, paths[0])
        except Exception as e:
            logger.warning("恢复后刷新校验码库异常 scene=%s: %s", scene_id, e)

    return {
        "scene_id": scene_id,
        "title": record.get("title", ""),
        "job_id": job_id,
        "new_scene_id": new_scene_id,
        "meta_restored": meta_restored,
        "paths": paths,
    }
