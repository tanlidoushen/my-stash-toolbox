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
from notify.telegram import send_notification
from scrape.merge import merge_plugin_into_scraped
from plugins.loader import PluginLoader

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
    """对 JAV 场景进行全量元数据写入（转发到公共模块 scrape/update）。

    2026-08-17 重构：与 enrich.update_scene_metadata 合并为统一写库入口
    scrape/update.update_scene_metadata。JAV 路径：add_tag="JAV" + set_stash_id=True。
    """
    from scrape.update import update_scene_metadata

    return await update_scene_metadata(
        client, scene_id, scraped_data, stash_box_index,
        add_tag="JAV", set_stash_id=True,
    )



async def _scrape_jav(client, scene_id, code, javstash_index, skip_notification=False, stash_path=None):
    """JAV 单场景完整刮削：javstash + URL 交叉引用 + 插件合并 + 写库 + 通知 + 校验码（run_scans/run_scrape_only 共用）。"""
    logger.info("      - 🔍 刮削 | 场景=%s | 番号=%s", scene_id, code)
    scraped_data = await scrape_japanese_scene(client, code, javstash_index)

    # ── JAV 交叉引用：从 javstash 场景/演员 URL 提取 stashdb ID 补抓 ──
    if scraped_data:
        from scrape.sources import JAV_CROSSREF_SOURCES
        from scrape.box import _fetch_scene_by_url_crossref, _merge_scraped, _enrich_single_source_with_crossref, _ensure_config_cache

        await _ensure_config_cache(client)

        jav_primary = JAV_CROSSREF_SOURCES[0]  # javstash
        jav_secondary = JAV_CROSSREF_SOURCES[1]  # stashdb

        # 1a. 场景 URL 交叉引用（封面/工作室/演员/标签/URL 全流程参与）
        secondary_data = await _fetch_scene_by_url_crossref(
            scraped_data, jav_primary, jav_secondary, client, scene_id,
        )
        if secondary_data:
            scraped_data = await _merge_scraped(
                scraped_data, secondary_data, jav_primary, jav_secondary,
                scene_id, client,
            )
            logger.info("      - ✅ JAV 场景 URL 交叉引用合并完成")
        else:
            # 1b. 演员 URL 交叉引用（仅当场景层没补到 stashdb 数据时）
            scraped_data = await _enrich_single_source_with_crossref(
                scraped_data, JAV_CROSSREF_SOURCES, client,
            )

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
        logger.info("   - [4/4] 应用元数据")
        await full_update_japanese_scene(client, scene_id, scraped_data, javstash_index)
        if not skip_notification:
            await send_notification(client, scene_id, is_japanese=True)
        # 校验码采集（可选，默认开）
        if Config.ENABLE_CHECKSUM:
            from stash.checksum import collect_checksums
            await collect_checksums(client, scene_id, stash_path)
        # 演员图库同步（后台线程，独立于调用方事件循环）
        if Config.PERFORMER_GALLERY_ENABLED:
            from scrape.performer_gallery import launch_gallery_sync
            launch_gallery_sync(scene_id, client)
        logger.info("   - 刮剃任务完成")
        return True
    logger.warning("      - 刮剃失败 | 番号=%s", code)
    return False


async def _scrape_jav_fp(client, scene_id, javstash_index, fp_hits, skip_notification=False, stash_path=None):
    """JAV 路径（指纹预查命中 javstash）完整刮削。

    与 _scrape_jav 的区别：番号来自 javstash 指纹命中的工作室代码（studio 字段），
    且 stashdb/tpdb 作为信息补充参与合并（参考 Non-JAV 的 enrich 逻辑）。

    fp_hits: fingerprint_detect 返回的命中 dict（javstash/stashdb/theporndb）。
    """
    from scrape.stashbox import scrape_japanese_scene
    from scrape.sources import get_source_by_name
    from scrape.box import _fetch_full

    # ── 1. 从 javstash 按指纹 stash_id 拉全量，拿工作室代码作为番号 ──
    javstash_sid = fp_hits.get("javstash")
    scraped_data = None
    code = None
    if javstash_sid:
        logger.info("      - 🔍 JAV 指纹命中 javstash=%s，拉全量", javstash_sid[:12])
        scraped_data = await _fetch_full(client, get_source_by_name("javstash"), javstash_sid, scene_id)
        if scraped_data:
            studio = scraped_data.get("studio") or {}
            code = scraped_data.get("code") or studio.get("code") or ""
            logger.info("      - 📇 JAV 工作室代码(番号)=%s | %s", code, scraped_data.get("title"))
            # stashdb/tpdb 信息补充：先从指纹预查的 stash_id 直接拉数据合并
            # （比 URL 交叉引用可靠，因为指纹预查已确认命中）
            from scrape.box import _merge_scraped, _ensure_config_cache
            from scrape.sources import JAV_CROSSREF_SOURCES
            await _ensure_config_cache(client)
            jav_primary = JAV_CROSSREF_SOURCES[0]  # javstash
            for secondary in JAV_CROSSREF_SOURCES[1:]:
                sec_sid = fp_hits.get(secondary.name)
                if sec_sid:
                    logger.info("      - 🔗 从指纹预查取 %s stash_id=%s，直接拉补充数据", secondary.name, sec_sid[:12])
                    sec_data = await _fetch_full(client, secondary, sec_sid, scene_id)
                    if sec_data:
                        scraped_data = await _merge_scraped(
                            scraped_data, sec_data, jav_primary, secondary,
                            scene_id, client,
                        )
                        logger.info("      - ✅ JAV %s 指纹补充合并完成", secondary.name)
            # 再跑 URL 交叉引用（补漏：演员级别 + 场景 URL 指向的其他源）
            scraped_data = await _jav_crossref_complement(client, scene_id, scraped_data)

    # ── 2. 插件继续（无论 javstash 是否成功），以 code 为参数 ──
    plugins = _get_plugins(client)
    for plugin in plugins:
        try:
            extra = await plugin.scrape(code, scene_info=scraped_data)
            if extra:
                if scraped_data:
                    merge_plugin_into_scraped(scraped_data, extra)
                else:
                    scraped_data = extra
        except Exception as e:
            logger.error("         - [Plugin:%s] Error: %s", plugin.name, e)

    if scraped_data:
        logger.info("   - [4/4] 应用元数据")
        await full_update_japanese_scene(client, scene_id, scraped_data, javstash_index)
        if not skip_notification:
            await send_notification(client, scene_id, is_japanese=True)
        if Config.ENABLE_CHECKSUM:
            from stash.checksum import collect_checksums
            await collect_checksums(client, scene_id, stash_path)
        if Config.PERFORMER_GALLERY_ENABLED:
            from scrape.performer_gallery import launch_gallery_sync
            launch_gallery_sync(scene_id, client)
        logger.info("   - 刮剃任务完成")
        return True
    logger.warning("      - 刮剃失败 | 场景=%s（javstash 指纹命中但无数据）", scene_id)
    return False


async def _jav_crossref_complement(client, scene_id, scraped_data):
    """JAV 场景的 stashdb/tpdb 信息补充（参考 Non-JAV enrich）。

    用 javstash 场景的 stash_id/URL 交叉引用 stashdb/tpdb，只补缺失的
    标签/URL/封面/演员信息，不覆盖 javstash 主数据。
    """
    from scrape.box import (_fetch_scene_by_url_crossref, _merge_scraped,
                            _enrich_single_source_with_crossref, _ensure_config_cache)
    from scrape.sources import JAV_CROSSREF_SOURCES

    await _ensure_config_cache(client)
    jav_primary = JAV_CROSSREF_SOURCES[0]  # javstash

    # 依次尝试 stashdb、theporndb 作补充源
    for secondary in JAV_CROSSREF_SOURCES[1:]:
        try:
            secondary_data = await _fetch_scene_by_url_crossref(
                scraped_data, jav_primary, secondary, client, scene_id,
            )
            if secondary_data:
                scraped_data = await _merge_scraped(
                    scraped_data, secondary_data, jav_primary, secondary,
                    scene_id, client,
                )
                logger.info("      - ✅ JAV %s 信息补充合并完成", secondary.name)
            else:
                scraped_data = await _enrich_single_source_with_crossref(
                    scraped_data, [jav_primary, secondary], client,
                )
        except Exception as e:
            logger.warning("      - ⚠️ JAV %s 补充异常: %s", secondary.name, e)
    return scraped_data


async def _submit_non_jav(client, scene_id, stash_box_index):
    """Non-JAV 提交 stash-box Identify job，返回 job_id。"""
    logger.info("      - 🔍 刮削 | 场景=%s", scene_id)
    return await scrape_scene(client, str(scene_id), stash_box_index)


async def _apply_non_jav(client, scene_id, stash_box_index, skip_notification=False, ws=None):
    """Non-JAV job 完成后：enrich + 通知 + 校验码。"""
    stash_id = await scene_mod.get_scene_stash_id(client, str(scene_id))
    if not stash_id:
        logger.warning("      - ⚠️ 跳过 | 场景=%s | 原因=无 stash_id", scene_id)
        return
    auto_index = await client.resolve_stash_box_index(
        await scene_mod.get_scene_info(client, str(scene_id)), stash_box_index
    )
    logger.info("      - ✅ 刮削完成 | stash_id=%s | index=%d", stash_id, auto_index)
    logger.info("      - 📝 更新元数据 | stash_id=%s | index=%d", stash_id, auto_index)
    await enrich_scene_metadata(client, str(scene_id), stash_id, auto_index)
    if not skip_notification:
        await send_notification(client, str(scene_id), is_japanese=False)
    # 校验码采集（可选，默认开）
    if Config.ENABLE_CHECKSUM:
        from stash.checksum import collect_checksums
        await collect_checksums(client, scene_id, None)
    # 演员图库同步（后台线程，独立于调用方事件循环）
    if Config.PERFORMER_GALLERY_ENABLED:
        from scrape.performer_gallery import launch_gallery_sync
        launch_gallery_sync(scene_id, client)


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
        # 判定优先级（2026-08-19 指纹预查优先）：
        #   1. 显式 forced_type
        #   2. 指纹预查三源（javstash→JAV / stashdb+tpdb→Non-JAV）
        #   3. 目录规则映射
        #   4. 文件名/番号检测（回退）
        is_japanese = None
        fp_hits = {}
        javstash_index = await client.resolve_stash_box_index_by_endpoint(
            Config.JAV_STASH_BOX_ENDPOINT, stash_box_index
        )

        if forced_type is not None:
            is_japanese = forced_type
        else:
            # 指纹预查（按场景逐一）
            for p in paths:
                scene_ids = await scene_mod.find_scenes_by_path(client, p)
                if not scene_ids:
                    continue
                from scrape.box import fingerprint_detect
                fp_hits = await fingerprint_detect(client, str(scene_ids[0]))
                if fp_hits.get("javstash"):
                    is_japanese = True
                    logger.info("   - [指纹判定] 类型=JAV（javstash 命中）")
                elif fp_hits.get("stashdb") or fp_hits.get("theporndb"):
                    is_japanese = False
                    logger.info("   - [指纹判定] 类型=Non-JAV（stashdb/tpdb 命中，javstash 未命中）")
                break
            if is_japanese is None:
                # 指纹未命中 → 目录规则 → 文件名回退
                if source_paths:
                    for sp, dp in zip(source_paths, paths):
                        dir_result = match_dir_rule(sp, dp)
                        if dir_result is not None:
                            is_japanese = dir_result
                            break
                if is_japanese is None:
                    is_japanese, _ = detect_japanese(paths, extract_japanese_code)

        scrape_jobs = []
        for p in paths:
            japanese_code = extract_japanese_code(p)

            scene_ids = await scene_mod.find_scenes_by_path(client, p)
            if not scene_ids:
                logger.info("      - ⏭️ 未找到场景: %s", p)
                continue

            for sid in scene_ids:
                # JAV 分支：指纹命中 javstash 时用工作室代码走插件，否则用文件名番号
                if is_japanese:
                    if fp_hits.get("javstash"):
                        await _scrape_jav_fp(client, sid, javstash_index, fp_hits,
                                             skip_notification, stash_path=p)
                    elif japanese_code:
                        await _scrape_jav(client, sid, japanese_code, javstash_index,
                                          skip_notification, stash_path=p)
                    elif forced_type is True:
                        logger.warning("      - ⚠️ 强制 JAV 但未提取到番号 | 场景=%s", sid)
                        continue
                    else:
                        # 指纹判定为 JAV 但无 javstash stash_id 且无文件名番号 → 尝试旧流程
                        await _scrape_jav(client, sid, japanese_code, javstash_index,
                                          skip_notification, stash_path=p)
                    continue

                # Non-JAV 分支（同原有逻辑）
                from scrape.box import scrape_scene_auto
                from scrape.update import update_scene_metadata

                scraped = await scrape_scene_auto(client, sid, "NONJAV")
                if not scraped:
                    logger.warning("      - ⚠️ 刮削无结果 | 场景=%s", sid)
                    continue
                current_info = await scene_mod.get_scene_info(client, sid)
                await update_scene_metadata(
                    client, sid, scraped, stash_box_index,
                    current_scene_info=current_info, add_tag="Non-JAV",
                )
                # ── 标记同步（双源 tt + TPDB）──
                if getattr(Config, "MARKER_SYNC_ENABLED", True):
                    from scrape.marker_sync import sync_markers_all
                    proxy = getattr(Config, "STASHBOX_PROXY", None)
                    mr = await sync_markers_all(client, sid, proxy=proxy)
                    if mr.get("markers"):
                        logger.info("      - 🎬 标记同步完成: %s", mr)
                if not skip_notification:
                    await send_notification(client, sid, is_japanese=False)
                if Config.ENABLE_CHECKSUM:
                    from stash.checksum import collect_checksums
                    await collect_checksums(client, sid, None)
                # 演员图库同步（后台线程）
                if Config.PERFORMER_GALLERY_ENABLED:
                    from scrape.performer_gallery import launch_gallery_sync
                    launch_gallery_sync(sid, client)

        # ---- 7: 刮削后处理 ----
        # 注：box 模式下 Non-JAV 已实时写库+通知，不需要等待循环
        logger.info("   - 🏃 刮削任务完成")
    finally:
        await _destroy_ws_subscriber(ws)


async def run_scrape_only(client, scene_id, file_path, stash_box_index=0, skip_notification=False, forced_type=None):
    """快速刮削：跳过扫描，直接从番号提取开始。"""
    logger.info("🔥 快速刮削 | 场景=%s | 路径=%s", scene_id, file_path)

    code = extract_japanese_code(file_path)
    fp_hits = {}
    if forced_type is not None:
        is_japanese = forced_type
    else:
        # 指纹预查优先（2026-08-19）：javstash→JAV / stashdb+tpdb→Non-JAV（参考 run_scans 判定）
        is_japanese = None
        fp_hits = {}
        try:
            from scrape.box import fingerprint_detect
            fp_hits = await fingerprint_detect(client, scene_id)
            if fp_hits.get("javstash"):
                is_japanese = True
                logger.info("   - [指纹判定] 类型=JAV（javstash 命中）")
            elif fp_hits.get("stashdb") or fp_hits.get("theporndb"):
                is_japanese = False
                logger.info("   - [指纹判定] 类型=Non-JAV（stashdb/tpdb 命中，javstash 未命中）")
        except Exception as e:
            logger.warning("         - ⚠️ 指纹预查异常（回退文件名校测）: %s", e)
        if is_japanese is None:
            is_japanese, _ = detect_japanese([file_path], extract_japanese_code)

    javstash_index = await client.resolve_stash_box_index_by_endpoint(
        Config.JAV_STASH_BOX_ENDPOINT, stash_box_index
    )

    # JAV 分支
    if is_japanese:
        if fp_hits.get("javstash"):
            await _scrape_jav_fp(client, scene_id, javstash_index, fp_hits,
                                 skip_notification, stash_path=file_path)
            return
        if code:
            await _scrape_jav(client, scene_id, code, javstash_index,
                              skip_notification, stash_path=file_path)
            return
        if forced_type is True:
            logger.warning("         - ⚠️ 强制 JAV 但未提取到番号 | 场景=%s", scene_id)
            return
        # 指纹判定 JAV 但无番号 → 走旧流程兜底
        await _scrape_jav(client, scene_id, code, javstash_index,
                          skip_notification, stash_path=file_path)
        return

    # Non-JAV: 统一刮削代理（box）—— 指纹直查 + 多源合并 + 一次写库
    logger.info("         - 🔍 Non-JAV 刮削（scrape-box）")
    from scrape.box import scrape_scene_auto
    from scrape.update import update_scene_metadata
    from stash import scene as scene_mod

    scraped = await scrape_scene_auto(client, scene_id, "NONJAV")
    if not scraped:
        logger.warning("         - ⚠️ 刮削无结果 | 场景=%s", scene_id)
        return

    # 获取当前场景信息（供增量写库）
    current_info = await scene_mod.get_scene_info(client, scene_id)
    await update_scene_metadata(
        client, scene_id, scraped, stash_box_index,
        current_scene_info=current_info, add_tag="Non-JAV",
    )
    # ── 标记同步（双源 tt + TPDB）──
    if getattr(Config, "MARKER_SYNC_ENABLED", True):
        from scrape.marker_sync import sync_markers_all
        proxy = getattr(Config, "STASHBOX_PROXY", None)
        mr = await sync_markers_all(client, scene_id, proxy=proxy)
        if mr.get("markers"):
            logger.info("         - 🎬 标记同步完成: %s", mr)
    if not skip_notification:
        from notify.telegram import send_notification
        await send_notification(client, scene_id, is_japanese=False)
    # 校验码采集
    if Config.ENABLE_CHECKSUM:
        from stash.checksum import collect_checksums
        await collect_checksums(client, scene_id, None)
    # 演员图库同步（后台线程）
    if Config.PERFORMER_GALLERY_ENABLED:
        from scrape.performer_gallery import launch_gallery_sync
        launch_gallery_sync(scene_id, client)
    logger.info("         - 🏃 快速刮削完成 (Non-JAV)")
