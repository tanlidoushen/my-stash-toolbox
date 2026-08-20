"""校验码采集：CD2 直取 + Stash 直取 + ed2k 流式，汇总落 SQLite。

触发：scrape/pipeline.py `run_scans` 刮削写库完成后调用（Config.ENABLE_CHECKSUM 默认开）。
设计：项目根 DESIGN-checksums.md。
"""

import asyncio
import logging
import sys

import httpx

from config import Config
from cd2 import get_cd2_client
from db import init_db, upsert_checksums, get_by_cd2_path
from stash import query as Q
from stash import tag as tag_mod

# vendor（pycryptodome）兜底注入；app.py 启动时已全局注入
_VENDOR = "/app/vendor"
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

logger = logging.getLogger(__name__)

# 采集用场景查询（含指纹/哈希/元数据）
SCENE_CHECKSUM_QUERY = """
query SceneChecksum($id: ID!) {
  findScene(id: $id) {
    id title code date
    files { path size fingerprints { type value } }
    tags { name }
    stash_ids { endpoint stash_id }
  }
}
"""


def _stash_path_to_cd2(file_path):
    from stash.delete import _stash_path_to_cd2 as _conv
    return _conv(file_path)


def _get_cd2_download_url(cd2_path):
    """获取 CD2 下载链接（GetDownloadUrlPath）。

    优先返回 CD2 转发链接（downloadUrlPath 占位符拼接，走 CD2 自身 19798 端口），
    拿不到时才用 115 CDN 直链（directUrl）兜底。

    规则（proto 注释）：scheme://host:port + downloadUrlPath，占位符
    {SCHEME}→http、{HOST}→gRPC server、{PREVIEW}→false。
    """
    client = get_cd2_client()
    d = client.GetDownloadUrlPath({
        "path": cd2_path, "preview": False, "get_direct_url": True,
    })
    if not d:
        return None
    # 类型 B：CD2 转发链接（优先）
    server = Config.CD2_SERVER  # host:port
    dl = d.downloadUrlPath or ""
    if dl:
        dl = dl.replace("{SCHEME}", "http").replace("{HOST}", server).replace("{PREVIEW}", "false")
        return "http://%s%s" % (server, dl)
    # 类型 A：115 CDN 直链（兜底）
    if d.directUrl:
        return d.directUrl
    return None


async def _collect_ed2k(download_url, file_size):
    """CD2 直链流式算 ed2k（httpx 流 + Ed2kHash 增量，任意 chunk 边界安全）。

    返回 hex 或 None（失败/超时）。
    """
    from ed2k import Ed2kHash
    timeout = Config.ED2K_TIMEOUT
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=15.0),
            follow_redirects=True,
        ) as c:
            async with c.stream("GET", download_url) as resp:
                resp.raise_for_status()
                h = Ed2kHash()
                size = 0
                async for chunk in resp.aiter_bytes():
                    if not chunk:
                        continue
                    h.update(chunk)
                    size += len(chunk)
                return size, h.hexdigest()
    except Exception as e:
        logger.warning("ed2k 流式计算失败（前 80 字符）%s: %s", download_url[:80], e)
        return None


async def collect_checksums(client, scene_id, stash_path=None, source="run_scans"):
    """采集一个场景主文件的全部校验码并落库。

    client: StashClient 实例（调用方复用，避免重复建连）；
    scene_id: Stash 场景 id；stash_path: Stash 内文件路径（主文件，None 取 files[0]）。
    返回 summary dict（幂等：ed2k 已算过且大小一致则跳过）。
    """
    init_db()
    data = await client.post(SCENE_CHECKSUM_QUERY, {"id": str(scene_id)})
    if not data or not data.get("findScene"):
        logger.warning("校验码采集: 场景 %s 查询失败，跳过", scene_id)
        return {"error": "scene not found"}

    scene = data["findScene"]
    files = scene.get("files") or []
    if not files:
        logger.warning("校验码采集: 场景 %s 无文件，跳过", scene_id)
        return {"error": "no files"}

    # 主文件 = 传入的 stash_path 对应的文件（多文件场景只主文件；None 取第一个）
    target = None
    if stash_path:
        for f in files:
            if f.get("path") == stash_path:
                target = f
                break
    if target is None:
        target = files[0]

    stash_path = target.get("path", "")
    file_size = target.get("size") or 0
    cd2_path = _stash_path_to_cd2(stash_path)

    # ── Stash 直取（零成本） ──
    checksums = {}
    for fp in (target.get("fingerprints") or []):
        t = (fp.get("type") or "").lower()
        v = fp.get("value")
        if t == "md5":
            checksums["md5"] = v
        elif t == "oshash":
            checksums["oshash"] = v
        elif t == "phash":
            checksums["phash"] = v
    if scene.get("code"):
        checksums["code"] = scene["code"]
    if scene.get("title"):
        checksums["title"] = scene["title"]
    # JAV/Non-JAV：场景标签体系（刮削时已打标签）。
    # ⚠️ 2026-08-17 修复：标签可能以别名命中（如「欧美制作」规范名 + Non-JAV 别名），
    # 必须用 tag.get_all_tags_with_aliases 反向映射，不能只比对规范名。
    all_tags = await tag_mod.get_all_tags_with_aliases(client)
    # 反向映射：别名 → 规范名（含规范名自身）
    alias_to_canonical = {}
    for canonical, aliases in all_tags.items():
        alias_to_canonical[canonical.lower()] = canonical
        for a in aliases or []:
            if a:
                alias_to_canonical[a.lower()] = canonical
    # 场景标签 → 规范化后的标签名集合
    tag_names = set()
    for t in (scene.get("tags") or []):
        name = t.get("name")
        if name:
            tag_names.add(alias_to_canonical.get(name.lower(), name))
    if "JAV" in tag_names:
        checksums["region"] = "JAV"
    elif "Non-JAV" in tag_names or "欧美制作" in tag_names:
        checksums["region"] = "Non-JAV"
    elif scene.get("code"):
        checksums["region"] = "JAV"  # 兜底：无标签但带番号
    if scene.get("stash_ids"):
        checksums["stash_ids"] = scene["stash_ids"]

    # ── CD2 直取（零成本） ──
    try:
        info = get_cd2_client().FindFileByPath(
            {"parentPath": "/", "path": cd2_path}
        )
        hashes = {}
        if info:
            # fileHashes: map<uint32,string>  1=Md5 2=Sha1 3=PikPakSha1
            for k, v in (info.fileHashes or {}).items():
                if k == 1:
                    hashes["md5"] = v
                elif k == 2:
                    hashes["sha1"] = v
        if hashes.get("sha1"):
            checksums["sha1"] = hashes["sha1"]
        if hashes.get("md5") and not checksums.get("md5"):
            checksums["md5"] = hashes["md5"]
    except Exception as e:
        logger.warning("校验码采集: CD2 哈希直取失败 %s: %s", cd2_path, e)

    # ── ed2k（唯一要下载的；幂等 = 内容指纹匹配，不用大小兜底） ──
    # 内容指纹（sha1=115盘权威 / oshash=Stash权威 / md5）全为零成本秒级直取，
    # 任一匹配即认为文件未变 → ed2k 跳过重算；全部不一致 → 文件内容变了 → 重算
    existing = get_by_cd2_path(cd2_path)
    if existing and existing.get("ed2k"):
        _same = (
            (existing.get("sha1") and checksums.get("sha1")
             and str(existing["sha1"]).lower() == str(checksums["sha1"]).lower())
            or (existing.get("oshash") and checksums.get("oshash")
                and str(existing["oshash"]).lower() == str(checksums["oshash"]).lower())
            or (existing.get("md5") and checksums.get("md5")
                and str(existing["md5"]).lower() == str(checksums["md5"]).lower())
        )
        if _same:
            checksums["ed2k"] = existing["ed2k"]  # 内容指纹一致 → 跳过重算
            logger.info("校验码采集: ed2k 命中缓存（内容指纹一致） %s", cd2_path)
        else:
            logger.info("校验码采集: 内容指纹变化，ed2k 重算 %s", cd2_path)
    if not checksums.get("ed2k"):
        max_size = Config.ED2K_MAX_SIZE
        if max_size > 0 and file_size > max_size:
            logger.info("校验码采集: 文件超 ED2K_MAX_SIZE(%d)，跳过 ed2k %s", max_size, cd2_path)
        else:
            try:
                url = _get_cd2_download_url(cd2_path)
                if url:
                    result = await _collect_ed2k(url, file_size)
                    if result:
                        _, ed2k_hex = result
                        checksums["ed2k"] = ed2k_hex
                        logger.info("校验码采集: ed2k 完成 %s (%d 字节)", cd2_path, file_size)
                    else:
                        logger.warning("校验码采集: ed2k 失败（留空不阻塞）%s", cd2_path)
                else:
                    logger.warning("校验码采集: 无下载直链，ed2k 跳过 %s", cd2_path)
            except Exception as e:
                logger.warning("校验码采集: ed2k 流程异常 %s: %s", cd2_path, e)

    upsert_checksums(cd2_path, scene_id, file_size, checksums, source=source)
    logger.info("校验码采集: 落库 %s | md5=%s sha1=%s ed2k=%s",
                cd2_path,
                "✓" if checksums.get("md5") else "—",
                "✓" if checksums.get("sha1") else "—",
                "✓" if checksums.get("ed2k") else "—")
    return {
        "cd2_path": cd2_path,
        "scene_id": str(scene_id),
        "file_size": file_size,
        "checksums": {k: v for k, v in checksums.items() if v},
    }


async def ensure_md5(client, scene_id, timeout=1200):
    """记录缺 md5 时补算：查场景路径 → metadataScan(rescan:true) 强制重扫 → 等完成 → 刷新库。

    历史文件 md5 只能靠 rescan 补（calculate_md5 全局配置已开；扫描时按配置计算）。
    返回 {"ok": True, "job_id", "status", "md5"} 或 {"error"}。
    """
    import asyncio
    import time

    from db import get_by_scene_id

    data = await client.post(SCENE_CHECKSUM_QUERY, {"id": str(scene_id)})
    scene = (data or {}).get("findScene")
    if not scene:
        return {"error": "scene not found"}
    files = scene.get("files") or []
    if not files:
        return {"error": "no files"}
    stash_path = files[0].get("path", "")
    if not stash_path:
        return {"error": "no file path"}

    from stash import query as Q
    d = await client.post(Q.METADATA_SCAN, {"input": {"paths": [stash_path], "rescan": True}})
    if not d:
        return {"error": "rescan submit failed"}
    job_id = d["metadataScan"]

    status = None
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = await client.post(Q.FIND_JOB, {"input": {"id": str(job_id)}})
        status = ((st or {}).get("findJob") or {}).get("status")
        if status in ("FINISHED", "FAILED", "CANCELLED"):
            break
        await asyncio.sleep(5)

    # 刷新库（md5 直取码更新；ed2k 幂等命中）
    await collect_checksums(client, scene_id, stash_path)
    row = get_by_scene_id(scene_id)
    return {
        "ok": True,
        "job_id": job_id,
        "status": status,
        "md5": (row or {}).get("md5"),
    }

