"""演员图库同步编排器 — 在场景刮削后自动为演员拉取 stash-box 图库。

调用方式（在 pipeline.py 中）：
    from scrape.performer_gallery import sync_performer_galleries
    asyncio.create_task(sync_performer_galleries(scene_id, client))

设计原则：
  - 直接复用 stash-performer-gallery-cli 的 sync.py（不重复造轮子）
  - 后台执行，不阻塞 Webhook 主流程
  - 幂等：index.json 存在即跳过
  - 按 performer_id 粒度加锁，避免并发冲突
"""

import asyncio
import json
import logging
import sys
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# ── 加载 gallery-cli 包 ──────────────────────────────────────────
# gallery-cli 源码通过 bind mount 挂载到 /app/performer_gallery_cli
_GALLERY_CLI_PATH = "/app/performer_gallery_cli"
if _GALLERY_CLI_PATH not in sys.path:
    sys.path.insert(0, _GALLERY_CLI_PATH)

# 延迟导入（在 async 函数内 import，避免模块加载时的顺序依赖）
# 但为了清晰，在模块级 import 类型提示用
# 实际调用时在 to_thread 内部再 import，确保线程安全


# ── 并发锁（按 performer_id 粒度） ──────────────────────────────
_performer_locks: dict[str, asyncio.Lock] = {}
_performer_locks_lock = asyncio.Lock()


async def _get_performer_lock(performer_id: str) -> asyncio.Lock:
    """获取或创建按 performer_id 粒度的锁。"""
    async with _performer_locks_lock:
        if performer_id not in _performer_locks:
            _performer_locks[performer_id] = asyncio.Lock()
        return _performer_locks[performer_id]


# ── 查询场景演员 ──────────────────────────────────────────────────

async def _get_scene_performers(client, scene_id: str) -> list[dict]:
    """从 Stash 查询场景的演员列表，返回 [{id, name, stash_ids}, ...]。"""
    # 用自定义查询带 gender 字段（FIND_SCENE 不含 gender）
    q = """query FindSceneWithGender($id: ID!) {
      findScene(id: $id) {
        id performers { id name gender stash_ids { endpoint stash_id } }
      }
    }"""
    data = await client.post(q, {"id": str(scene_id)})
    if not data:
        logger.warning("   - ⚠️ 场景 %s 不存在，跳过图库同步", scene_id)
        return []
    scene = data.get("findScene") or {}
    performers = scene.get("performers") or []
    return performers


# ── 幂等检查 ──────────────────────────────────────────────────────

def _is_gallery_synced(pdir: Path) -> bool:
    """检查演员图库是否已同步过（index.json 存在且非空）。"""
    index_file = pdir / "index.json"
    if not index_file.exists():
        return False
    try:
        index = json.loads(index_file.read_text())
        galleries = index.get("galleries") or {}
        return len(galleries) > 0
    except (json.JSONDecodeError, OSError):
        return False


# ── 单演员同步（后台线程） ────────────────────────────────────────

async def _sync_one_performer(
    performer_id: str,
    performer_name: str,
    scene_id: str,
    stash_url: str,
    download_path: str,
    proxy: str,
    flaresolverr_url: str,
    run_scraper: bool,
    run_babepedia: bool,
    run_indexxx: bool,
) -> dict | None:
    """在后台线程中调用 gallery-cli 的 process_performer() 完成图库同步。

    Returns:
        None（已同步/跳过）或 dict:
            {name, pid, images_downloaded: int, gallery_created: int, total_actions: int}
    """
    lock = await _get_performer_lock(performer_id)
    async with lock:
        try:
            def _run():
                """在后台线程中执行同步的 gallery-cli 流程（屏蔽 print 输出）。"""
                import sys
                from io import StringIO
                from stash_performer_gallery.stash_client import StashClient
                from stash_performer_gallery.sync import process_performer, ActionLog

                # 屏蔽 process_performer 内部的 print 输出
                old_stdout = sys.stdout
                sys.stdout = StringIO()
                try:
                    gal_stash = StashClient(stash_url)
                    actions = ActionLog(apply=True)
                    process_performer(
                        performer_id=performer_id,
                        stash=gal_stash,
                        download_path=download_path,
                        proxy=proxy,
                        run_scraper=run_scraper,
                        run_babepedia=run_babepedia,
                        run_indexxx=run_indexxx,
                        flaresolverr_url=flaresolverr_url,
                        apply=True,
                        actions=actions,
                    )
                finally:
                    sys.stdout = old_stdout
                return actions

            actions = await asyncio.to_thread(_run)
            if actions.count == 0:
                logger.info("   - 🖼️ 图库已是最新: %s (%s)", performer_name, performer_id)
                return None
            else:
                # 统计图片数
                img_count = sum(1 for k, _ in actions.actions if k == "image_download")
                gal_count = sum(1 for k, _ in actions.actions if k == "gallery_create")
                logger.info(
                    "   - 🖼️ 图库同步完成: %s (%s) | %s",
                    performer_name, performer_id, actions.summary,
                )
                return {
                    "name": performer_name,
                    "pid": performer_id,
                    "images_downloaded": img_count,
                    "gallery_created": gal_count,
                    "total_actions": actions.count,
                }
        except Exception as e:
            logger.error(
                "   - ❌ 图库同步失败 performer=%s (%s) scene=%s: %s",
                performer_name, performer_id, scene_id, e,
                exc_info=True,
            )
            return None


# ── 主入口 ──────────────────────────────────────────────────────────

def launch_gallery_sync(scene_id, client, performer_ids: list[str] | None = None):
    """在后台线程中为场景演员同步图库（不依赖调用方的事件循环）。

    任何调用方式（asyncio.run / await / 后台线程）下都能工作：
    整个流程（查演员+同步图库）都在独立的守护线程 + 专属事件循环中执行，
    不依赖调用方 `asyncio.run()` 的生命周期（asyncio.run 返回会取消
    pending 的 asyncio.create_task，导致图库同步从未真正执行）。
    """
    from config import Config

    if not getattr(Config, "PERFORMER_GALLERY_ENABLED", True):
        logger.debug("   - 🖼️ 图库同步已禁用（PERFORMER_GALLERY_ENABLED=false）")
        return

    # 收集配置参数（当前线程读取，避免跨线程共享 Config 对象）
    stash_url = Config.STASH_URL
    download_path = getattr(Config, "PERFORMER_GALLERY_PATH", "/path/to/performer-gallery")
    proxy = getattr(Config, "STASHBOX_PROXY", "http://<proxy>:7890")

    # 在后台线程中执行完整流程（独立事件循环，不依赖调用方）
    t = threading.Thread(
        target=_run_gallery_sync_in_thread,
        args=(scene_id, stash_url, download_path, proxy),
        kwargs={"performer_ids": performer_ids},
        daemon=True,
    )
    t.start()


def _run_gallery_sync_in_thread(
    scene_id: str,
    stash_url: str,
    download_path: str,
    proxy: str,
    performer_ids: list[str] | None = None,
):
    """在独立线程 + 专属事件循环中运行图库同步。"""
    try:
        asyncio.run(_sync_performers_inner(
            scene_id=scene_id,
            stash_url=stash_url,
            download_path=download_path,
            proxy=proxy,
            performer_ids=performer_ids,
        ))
    except Exception as e:
        logger.error("   - ❌ 图库后台同步异常 scene=%s: %s", scene_id, e, exc_info=True)


async def _sync_performers_inner(
    scene_id: str,
    stash_url: str,
    download_path: str,
    proxy: str,
    performer_ids: list[str] | None = None,
):
    """在后台图库同步线程中执行：查演员 + 同步图库。"""
    from config import Config

    # 新建独立的 StashClient（不复用调用方 client，线程安全）
    from stash.client import StashClient
    client = StashClient(stash_url, api_key=Config.STASH_APIKEY)

    # 获取演员 ID + 信息（含 stash_ids）
    if performer_ids:
        pids = performer_ids
        pinfo = {}
        for pid in pids:
            data = await client.post(
                "query($id: ID!) { findPerformer(id: $id) { id name stash_ids { endpoint stash_id } } }",
                {"id": str(pid)},
            )
            p = (data or {}).get("findPerformer")
            if p:
                pinfo[pid] = {
                    "name": p.get("name", pid),
                    "stash_ids": p.get("stash_ids") or [],
                }
    else:
        performers = await _get_scene_performers(client, scene_id)
        if not performers:
            logger.debug("   - 🖼️ 场景 %s 无演员，跳过图库同步", scene_id)
            return
        # 过滤出有 stash_ids 且性别匹配的
        valid = [p for p in performers if p.get("stash_ids")]
        if not valid:
            logger.info("   - 🖼️ 场景 %s 演员均无 stash_ids，跳过图库同步", scene_id)
            return
        allowed_genders = getattr(Config, "PERFORMER_GALLERY_GENDERS", None)
        if allowed_genders:
            allowed_set = {g.strip().upper() for g in allowed_genders if g.strip()}
            before = len(valid)
            valid = [p for p in valid if (p.get("gender") or "").upper() in allowed_set]
            skipped = before - len(valid)
            if skipped:
                logger.info("   - 🖼️ 跳过 %d 个演员（性别不匹配）", skipped)
        pids = [p["id"] for p in valid]
        pinfo = {p["id"]: {"name": p.get("name", p["id"]),
                           "stash_ids": p.get("stash_ids") or []} for p in valid}

    if not pids:
        logger.info("   - 🖼️ 场景 %s 无可同步演员（stash_ids 为空或性别不匹配）", scene_id)
        return

    logger.info("   - 🖼️ 图库同步已派发: %d 个演员 | scene=%s", len(pids), scene_id)

    # 配置参数
    run_scraper = getattr(Config, "PERFORMER_GALLERY_SCRAPER", False)
    run_babepedia = getattr(Config, "PERFORMER_GALLERY_BABEPEDIA", False)
    run_indexxx = getattr(Config, "PERFORMER_GALLERY_INDEXXX", False)
    flaresolverr_url = "http://<flaresolverr>:8191"

    # 同步图库（幂等检查 + 派发任务）
    tasks = []
    task_pids = []
    for pid in pids:
        pdir = Path(download_path) / str(pid)
        if _is_gallery_synced(pdir):
            logger.debug("   - 🖼️ 图库已同步: %s", pid)
            continue
        task_pids.append(pid)
        tasks.append(
            _sync_one_performer(
                performer_id=pid,
                performer_name=pinfo[pid]["name"],
                scene_id=scene_id,
                stash_url=stash_url,
                download_path=download_path,
                proxy=proxy,
                flaresolverr_url=flaresolverr_url,
                run_scraper=run_scraper,
                run_babepedia=run_babepedia,
                run_indexxx=run_indexxx,
            )
        )

    if tasks:
        results = await asyncio.gather(*tasks)
        scene_code = await _get_scene_code(client, scene_id)
        scene_tag = f" ({scene_code})" if scene_code else ""

        # 构建每个演员的明细
        details = []
        total_images = 0
        for r in results:
            if r is None:
                continue
            pid = r["pid"]
            stash_ids = _format_stash_ids(pinfo.get(pid, {}).get("stash_ids", []))
            img_count = r["images_downloaded"]
            total_images += img_count
            details.append(
                f"  {r['name']}\n"
                f"    stash_id: {stash_ids[0] if stash_ids else '-'}\n"
                f"    图库: {img_count}张图"
            )

        if details:
            # 日志汇总
            logger.info(
                "   - ✅ 图库同步全部完成: %d/%d 演员 | 场景=%s%s | 共%d张图",
                len(details), len(pids), scene_id, scene_tag, total_images,
            )
            # TG 通知
            _send_gallery_notification(scene_id, scene_code, details, total_images)
    else:
        logger.info("   - 🖼️ 图库同步跳过: 场景 %s 所有演员已同步过", scene_id)


def _format_stash_ids(stash_ids: list[dict]) -> list[str]:
    """格式化 stash_ids 为 ["域名:id", ...] 的列表。

    原样取 endpoint 域名，拼上完整 stash_id。
    """
    from urllib.parse import urlparse
    result = []
    for s in stash_ids:
        ep = s.get("endpoint", "")
        sid = s.get("stash_id", "")
        try:
            domain = urlparse(ep).netloc or ep
        except Exception:
            domain = ep
        result.append(f"{domain}:{sid}")
    return result


async def _get_scene_code(client, scene_id: str) -> str:
    """查询场景番号（用于 TG 通知）。"""
    try:
        q = "query($id: ID!) { findScene(id: $id) { code } }"
        data = await client.post(q, {"id": str(scene_id)})
        scene = (data or {}).get("findScene") or {}
        return (scene.get("code") or "").strip()
    except Exception:
        return ""


def _send_gallery_notification(scene_id: str, scene_code: str, details: list[str], total_images: int):
    """在守护线程中发送图库同步完成的 TG 通知。"""
    import threading
    t = threading.Thread(target=_send_gallery_notification_sync,
                         args=(scene_id, scene_code, details, total_images), daemon=True)
    t.start()


def _send_gallery_notification_sync(scene_id: str, scene_code: str, details: list[str], total_images: int):
    """同步发送 TG 通知（在独立线程中执行）。"""
    try:
        import asyncio
        from notify.sender import send_html
        from config import Config

        code_tag = f" ({scene_code})" if scene_code else ""
        actor_count = len(details)
        detail_lines = "\n".join(details)
        text = (
            "🖼️ <b>图库同步完成</b>\n\n"
            f"🎬 场景: <a href=\"{Config.STASH_BASE_URL}/scenes/{scene_id}\">{scene_id}</a>{code_tag}\n"
            "─────────────────\n"
            f"{detail_lines}\n"
            "─────────────────\n"
            f"✅ 新增图库: {actor_count} 个演员 | 共 {total_images} 张图"
        )
        asyncio.run(send_html(Config.TG_CHAT_ID, text))
    except Exception as e:
        logger.warning("图库同步 TG 通知发送失败: %s", e)


async def sync_performer_galleries(
    scene_id,
    client,
    performer_ids: list[str] | None = None,
):
    """为场景中的演员同步图库，后台执行不阻塞。

    参数:
        scene_id: Stash 场景 ID
        client: webhook-scanner 的 async StashClient（httpx）
        performer_ids: 可选，指定演员 ID 列表（不传则从场景查）

    从 Config 读取：
        PERFORMER_GALLERY_ENABLED
        PERFORMER_GALLERY_PATH
        PERFORMER_GALLERY_SCRAPER
        PERFORMER_GALLERY_BABEPEDIA
        PERFORMER_GALLERY_INDEXXX
        STASH_URL
        STASHBOX_PROXY
    """
    from config import Config

    if not getattr(Config, "PERFORMER_GALLERY_ENABLED", True):
        logger.debug("   - 🖼️ 图库同步已禁用（PERFORMER_GALLERY_ENABLED=false）")
        return

    # 获取演员列表
    if performer_ids:
        performers = []
        for pid in performer_ids:
            data = await client.post(
                "query($id: ID!) { findPerformer(id: $id) { id name gender stash_ids { endpoint stash_id } } }",
                {"id": str(pid)},
            )
            p = (data or {}).get("findPerformer")
            if p:
                performers.append(p)
    else:
        performers = await _get_scene_performers(client, scene_id)

    if not performers:
        logger.debug("   - 🖼️ 场景 %s 无演员，跳过图库同步", scene_id)
        return

    # 过滤出有 stash_ids 且性别匹配的演员
    valid = [p for p in performers if p.get("stash_ids")]
    if not valid:
        logger.info("   - 🖼️ 场景 %s 演员均无 stash_ids，跳过图库同步", scene_id)
        return
    # 性别过滤
    allowed_genders = getattr(Config, "PERFORMER_GALLERY_GENDERS", None)
    if allowed_genders:
        allowed_set = {g.strip().upper() for g in allowed_genders if g.strip()}
        before = len(valid)
        valid = [p for p in valid if (p.get("gender") or "").upper() in allowed_set]
        skipped = before - len(valid)
        if skipped:
            logger.info("   - 🖼️ 跳过 %d 个演员（性别不匹配）", skipped)

    # 配置参数
    download_path = getattr(Config, "PERFORMER_GALLERY_PATH", "/path/to/performer-gallery")
    proxy = getattr(Config, "STASHBOX_PROXY", "http://<proxy>:7890")
    flaresolverr_url = "http://<flaresolverr>:8191"
    stash_url = Config.STASH_URL
    run_scraper = getattr(Config, "PERFORMER_GALLERY_SCRAPER", False)
    run_babepedia = getattr(Config, "PERFORMER_GALLERY_BABEPEDIA", False)
    run_indexxx = getattr(Config, "PERFORMER_GALLERY_INDEXXX", False)

    # 对每个演员发起后台同步
    for p in valid:
        pid = p["id"]
        pname = p.get("name", "?")
        pdir = Path(download_path) / str(pid)

        if _is_gallery_synced(pdir):
            logger.debug("   - 🖼️ 图库已同步: %s (%s)", pname, pid)
            continue

        logger.info(
            "   - 🖼️ 图库同步已派发: %s (%s) | stash_ids=%d",
            pname, pid, len(p.get("stash_ids", [])),
        )
        asyncio.create_task(
            _sync_one_performer(
                performer_id=pid,
                performer_name=pname,
                scene_id=scene_id,
                stash_url=stash_url,
                download_path=download_path,
                proxy=proxy,
                flaresolverr_url=flaresolverr_url,
                run_scraper=run_scraper,
                run_babepedia=run_babepedia,
                run_indexxx=run_indexxx,
            )
        )