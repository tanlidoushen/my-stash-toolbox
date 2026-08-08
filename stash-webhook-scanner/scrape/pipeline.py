"""流水线编排 —— run_scans / run_scrape_only 主流程。

每个刮削任务独立创建和销毁 WebSocket 订阅器（StashWSSubscriber），
确保断连不会拖死后续任务；订阅器通过 ping_interval 自动检测死连接。
"""

import asyncio
import logging
import os

from config import Config
from stash.client import StashClient
from stash import scanner as scan_mod
from stash import scene as scene_mod
from stash import tag as tag_mod
from stash import studio as studio_mod
from stash import performer as performer_mod
from stash.ws_subscriber import StashWSSubscriber
from scrape.code import extract_japanese_code
from scrape.detector import detect_japanese, match_dir_rule
from scrape.stashbox import scrape_japanese_scene, scrape_scene
from scrape.enrich import enrich_scene_metadata
from scrape.merge import merge_plugin_into_scraped
from plugins.loader import PluginLoader
from notify.telegram import send_notification

logger = logging.getLogger(__name__)

# 全局缓存插件加载器（应用启动时初始化）
_plugin_loader_instance = None


def _get_plugins(client):
    """获取所有插件（全局缓存，惰性初始化）。"""
    global _plugin_loader_instance
    if _plugin_loader_instance is None:
        _plugin_loader_instance = PluginLoader(Config.PLUGIN_DIR)
    return _plugin_loader_instance.discover(stash_client=client)


# ── WS Subscriber 工具函数 ──────────────────────────────

def _build_ws_url() -> str:
    ws_url = Config.STASH_WS_URL
    if not ws_url:
        http_url = Config.STASH_URL
        ws_url = http_url.replace("http://", "ws://").replace("https://", "wss://")
    return ws_url


async def _create_ws_subscriber() -> StashWSSubscriber | None:
    """为当前刮削任务创建一个独立的 WS 订阅器。"""
    try:
        ws = StashWSSubscriber(
            _build_ws_url(), api_key=getattr(Config, "STASH_APIKEY", None),
            ping_interval=30, pong_timeout=10,
        )
        await ws.start()
        try:
            await asyncio.wait_for(ws._connected.wait(), timeout=5)
            if ws.is_connected:
                logger.info("   - 📡 WS 已连接 | %s", _build_ws_url())
            else:
                logger.warning("   - ⚠️ WS 连接超时(%s)，将用 HTTP 轮询", _build_ws_url())
        except asyncio.TimeoutError:
            logger.warning("   - ⚠️ WS 连接超时，将用 HTTP 轮询")
        return ws
    except Exception as e:
        logger.warning("   - ⚠️ WS 订阅器创建失败: %s，将使用 HTTP 轮询", e)
        return None


async def _destroy_ws_subscriber(ws: StashWSSubscriber | None):
    if ws is not None:
        try:
            await ws.stop()
        except Exception as e:
            logger.debug("WS destroy 异常: %s", e)


# ── 核心函数 ──────────────────────────────────────────────

async def full_update_japanese_scene(client, scene_id, scraped_data, stash_box_index=0):
    """对 JAV 场景进行全量元数据写入（标题、番号、日期、片商、演员、标签等）。"""
    logger.info("      - 📝 全量更新 | 场景=%s", scene_id)

    input_data = {"id": str(scene_id)}

    for field in ("title", "code", "date", "director", "details"):
        val = scraped_data.get(field)
        if val:
            input_data[field] = val

    cover_image = scraped_data.get("image")
    if cover_image:
        input_data["cover_image"] = cover_image

    studio = scraped_data.get("studio")
    studio_id = None
    if studio:
        if studio.get("stored_id"):
            studio_id = studio["stored_id"]
        elif studio.get("name"):
            studio_id = await studio_mod.create_or_find_studio(client, studio, stash_box_index)
        if studio_id:
            input_data["studio_id"] = studio_id

    performers = scraped_data.get("performers", [])
    performer_ids = []
    for p in performers:
        if not p.get("name"):
            continue
        if p.get("stored_id"):
            performer_ids.append(p["stored_id"])
        else:
            pid = await performer_mod.create_or_find_performer(client, p, stash_box_index)
            if pid:
                performer_ids.append(pid)
    if performer_ids:
        input_data["performer_ids"] = performer_ids

    tags = scraped_data.get("tags", [])
    tag_ids = []
    for t in tags:
        name = t.get("name")
        if not name:
            continue
        tid = await tag_mod.create_or_find_tag(client, name)
        if tid:
            tag_ids.append(tid)
    jav_tag_id = await tag_mod.create_or_find_tag(client, "JAV", verbose=False)
    if jav_tag_id and jav_tag_id not in tag_ids:
        tag_ids.append(jav_tag_id)
    if tag_ids:
        input_data["tag_ids"] = tag_ids

    remote_site_id = scraped_data.get("remote_site_id")
    if remote_site_id:
        endpoint = await client.get_endpoint(stash_box_index)
        input_data["stash_ids"] = [{"endpoint": endpoint, "stash_id": remote_site_id}]

    urls = scraped_data.get("urls") or []
    if urls:
        input_data["urls"] = urls

    input_data = {k: v for k, v in input_data.items() if v is not None and v != [] and v != {} and v != ""}
    if len(input_data) == 1:
        logger.info("         - ⏭️ 无变更")
        return False

    return await scene_mod.update_scene(client, input_data)


async def run_scans(stash_url, paths, do_scrape=True, stash_box_index=0, skip_notification=False, source_paths=None, forced_type=None):
    """
    完整流程：
      1. 简单扫描（路径入库）
      2. 等待完成
      3. 详细扫描（生成预览/指纹等）
      4. 等待完成
      5. 按路径查找场景 ID
      6. 对每个场景执行 Stash-box 刮削
      7. 等待刮削完成，执行元数据补充
      forced_type: True=强制JAV / False=强制Non-JAV / None=自动检测
    """
    logger.info("🔄 刮削任务 | 路径=%s", " | ".join(paths))

    client = StashClient(stash_url, api_key=Config.STASH_APIKEY)
    ws = await _create_ws_subscriber()
    try:
        # ---- 1 & 2: 简单扫描 + 等待 ----
        logger.info("   - [1/4] 简单扫描")
        simple_job = await scan_mod.scan_simple(client, paths)
        if simple_job is None:
            logger.error("   - ❌ 简单扫描失败，流水线终止")
            return
        if await scan_mod.wait_for_job(client, simple_job, ws_subscriber=ws) is None:
            logger.warning("   - ⏭️ 简单扫描任务已被遗忘，继续后续步骤")

        # ---- 3 & 4: 详细扫描 + 等待 ----
        logger.info("   - [2/4] 详细扫描")
        detailed_job = await scan_mod.scan_detailed(client, paths)
        if detailed_job is None:
            logger.error("   - ❌ 详细扫描失败，流水线终止")
            return
        if await scan_mod.wait_for_job(client, detailed_job, ws_subscriber=ws) is None:
            logger.warning("   - ⏭️ 详细扫描任务已被遗忘，继续后续步骤")

        if not do_scrape:
            return

        # ---- 5 & 6: 查场景 + 刮削 ----
        # 强制类型优先，其次目录规则映射（仅 webhook 通知触发时生效），最后文件名检测
        is_japanese = None
        if forced_type is not None:
            is_japanese = forced_type
        elif source_paths:
            for sp, dp in zip(source_paths, paths):
                dir_result = match_dir_rule(sp, dp)
                if dir_result is not None:
                    is_japanese = dir_result
                    break
        if is_japanese is None:
            is_japanese, _ = detect_japanese(paths, extract_japanese_code)

        javstash_index = await client.resolve_stash_box_index_by_endpoint(
            Config.JAV_STASH_BOX_ENDPOINT, stash_box_index
        )

        scrape_jobs = []
        for p in paths:
            japanese_code = extract_japanese_code(p)

            scene_ids = await scene_mod.find_scenes_by_path(client, p)
            if not scene_ids:
                logger.info("      - ⏭️ 未找到场景: %s", p)
                continue

            for sid in scene_ids:
                if is_japanese and japanese_code:
                    logger.info("      - 🔍 刮削 | 场景=%s | 番号=%s", sid, japanese_code)
                    scraped_data = await scrape_japanese_scene(client, japanese_code, javstash_index)

                    # 调用所有插件（无论 javstash 是否成功），传递 scene_info 供兗底判断
                    plugins = _get_plugins(client)
                    for plugin in plugins:
                        try:
                            extra = await plugin.scrape(japanese_code, scene_info=scraped_data)
                            if extra:
                                if scraped_data:
                                    merge_plugin_into_scraped(scraped_data, extra)
                                else:
                                    scraped_data = extra  # 插件兗底返回了完整数据
                        except Exception as e:
                            logger.error("         - [Plugin:%s] Error: %s", plugin.name, e)

                    if scraped_data:
                        logger.info("   - [4/4] 应用元数据")
                        await full_update_japanese_scene(client, sid, scraped_data, javstash_index)
                        if not skip_notification:
                            await send_notification(client, sid, is_japanese=True)
                        logger.info("   - 刮剃任务完成")
                    else:
                        logger.warning("      - 刮剃失败 | 番号=%s", japanese_code)
                elif is_japanese and forced_type is True:
                    logger.warning("      - ⚠️ 强制 JAV 但未提取到番号 | 场景=%s", sid)
                    continue
                else:
                    logger.info("      - 🔍 刮削 | 场景=%s", sid)
                    job_id = await scrape_scene(client, sid, stash_box_index)
                    if job_id:
                        scrape_jobs.append((job_id, sid))

        # ---- 7: 等待 stash-box 刮削完成 + 元数据补充 ----
        if not scrape_jobs:
            return
        logger.info("   - [4/4] 应用元数据")
        for job_id, sid in scrape_jobs:
            status = await scan_mod.wait_for_job(client, job_id, ws_subscriber=ws)
            if status is None or status.get("status") != "FINISHED":
                logger.warning(
                    "      - ⚠️ 刮削未完成 | 场景=%s | 状态=%s",
                    sid, status.get("status") if status else "未知",
                )
                continue
            stash_id = await scene_mod.get_scene_stash_id(client, sid)
            if not stash_id:
                logger.warning("      - ⚠️ 跳过 | 场景=%s | 原因=无 stash_id", sid)
                continue
            auto_index = await client.resolve_stash_box_index(
                await scene_mod.get_scene_info(client, sid), stash_box_index
            )
            logger.info("      - ✅ 刮削完成 | 场景=%s", sid)
            logger.info("      - 📝 更新元数据 | stash_id=%s | index=%d", stash_id, auto_index)
            await enrich_scene_metadata(client, sid, stash_id, auto_index)
            if not skip_notification:
                await send_notification(client, sid, is_japanese=False)
            logger.info("   - 🏃 刮削任务完成")
    finally:
        await _destroy_ws_subscriber(ws)


async def run_scrape_only(client, scene_id, file_path, stash_box_index=0, skip_notification=False, forced_type=None):
    """快速刮削：跳过扫描，直接从番号提取开始。"""
    logger.info("🔥 快速刮削 | 场景=%s | 路径=%s", scene_id, file_path)

    code = extract_japanese_code(file_path)
    if forced_type is not None:
        is_japanese = forced_type
    else:
        is_japanese, _ = detect_japanese([file_path], extract_japanese_code)

    if is_japanese and code:
        javstash_index = await client.resolve_stash_box_index_by_endpoint(
            Config.JAV_STASH_BOX_ENDPOINT, stash_box_index
        )
        logger.info("         - 🔍 JAV 刮削 | 番号=%s", code)
        scraped_data = await scrape_japanese_scene(client, code, javstash_index)

        # 调用所有插件（无论 javstash 是否成功），传递 scene_info 供兗底判断
        plugins = _get_plugins(client)
        for plugin in plugins:
            try:
                extra = await plugin.scrape(code, scene_info=scraped_data)
                if extra:
                    if scraped_data:
                        merge_plugin_into_scraped(scraped_data, extra)
                    else:
                        scraped_data = extra  # 插件兗底返回了完整数据
            except Exception as e:
                logger.error("         - [Plugin:%s] Error: %s", plugin.name, e)

        if scraped_data:
            await full_update_japanese_scene(client, scene_id, scraped_data, javstash_index)
            if not skip_notification:
                await send_notification(client, scene_id, is_japanese=True)
            logger.info("         - 快速刮剃完成 (JAV)")
        else:
            logger.warning("         - JAV 刮剃失败 | 番号=%s", code)
        return

    if is_japanese and forced_type is True:
        logger.warning("         - ⚠️ 强制 JAV 但未提取到番号 | 场景=%s", scene_id)
        return

    # Non-JAV: stash-box scratch scrape → 需要 WS 订阅
    logger.info("         - 🔍 Non-JAV 刮削")
    ws = await _create_ws_subscriber()
    try:
        job_id = await scrape_scene(client, str(scene_id), stash_box_index)
        if not job_id:
            logger.warning("         - ⚠️ 刮削作业提交失败")
            return

        status = await scan_mod.wait_for_job(client, job_id, ws_subscriber=ws)
        if status is None or status.get("status") != "FINISHED":
            logger.warning("         - ⚠️ 刮削未完成 | 状态=%s",
                           status.get("status") if status else "未知")
            return

        stash_id = await scene_mod.get_scene_stash_id(client, str(scene_id))
        if not stash_id:
            logger.warning("         - ⚠️ 跳过 | 原因=无 stash_id")
            return

        auto_index = await client.resolve_stash_box_index(
            await scene_mod.get_scene_info(client, str(scene_id)), stash_box_index
        )
        logger.info("         - ✅ 刮削完成 | stash_id=%s | index=%d", stash_id, auto_index)
        await enrich_scene_metadata(client, str(scene_id), stash_id, auto_index)
        if not skip_notification:
            await send_notification(client, str(scene_id), is_japanese=False)
        logger.info("         - 🏃 快速刮削完成 (Non-JAV)")
    finally:
        await _destroy_ws_subscriber(ws)
