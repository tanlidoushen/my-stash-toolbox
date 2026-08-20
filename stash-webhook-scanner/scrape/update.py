"""统一 Stash 元数据写库模块（2026-08-17 重构）。

合并原 full_update_japanese_scene（JAV）与 enrich.update_scene_metadata（Non-JAV）
两套几乎重复的"scraped_data → 写本地场景"逻辑为一个公共函数。

行为统一（取两者更安全语义）：
- 演员：保留当前场景演员 + 增量添加刮削演员（不误删已有）
- 标签：compare_tags 差集比对，只加不删；按 add_tag 打 JAV/Non-JAV 标签
- stash_id / urls：仅 JAV 刮削数据有，set_stash_id=True 时写入
"""
import logging

from stash import scene as scene_mod
from stash import tag as tag_mod
from stash import performer as performer_mod
from stash import studio as studio_mod

logger = logging.getLogger(__name__)

# 外键约束失败特征：场景写入引用了不存在的 tag/studio/performer id
# （最常见原因 = 标签缓存 _tag_cache 过期，Stash 侧已删除/合并标签）
_FK_ERROR_MARK = "FOREIGN KEY constraint failed"


async def _resolve_tag_ids(client, current_tags, scraped_tags, add_tag=None):
    """解析 tag_ids：compare_tags 差集（只加不删）+ add_tag 语言标签。

    与 update_scene_metadata 内的逻辑一致，抽成独立函数以便失败重试时复用。
    """
    need_update_tags, reason, merged_names = await tag_mod.compare_tags(
        client, current_tags, scraped_tags
    )
    if need_update_tags:
        tag_ids = [t["id"] for t in current_tags]
        all_tags = await tag_mod.get_all_tags_with_aliases(client)
        norm_current = {
            tag_mod.normalize_tag_name(t["name"], all_tags) for t in current_tags
        }
        for tag_name in merged_names:
            if tag_mod.normalize_tag_name(tag_name, all_tags) not in norm_current:
                tid = await tag_mod.create_or_find_tag(client, tag_name)
                if tid:
                    tag_ids.append(tid)
    else:
        tag_ids = [t["id"] for t in current_tags]

    if add_tag:
        lang_tag_id = await tag_mod.create_or_find_tag(client, add_tag, verbose=False)
        if lang_tag_id and lang_tag_id not in tag_ids:
            tag_ids.append(lang_tag_id)
    return tag_ids


async def update_scene_metadata(client, scene_id, scraped_data, stash_box_index=0,
                                current_scene_info=None, add_tag=None, set_stash_id=False):
    """把刮削数据写入本地 Stash 场景（统一入口）。

    Args:
        client: StashClient
        scene_id: 本地场景 id
        scraped_data: 刮削返回数据（title/code/date/director/details/image/studio/
                      performers/tags/remote_site_id/urls）
        stash_box_index: stash-box 实例索引（创建 studio/performer 用）
        current_scene_info: 当前场景信息（Non-JAV 传入做增量；JAV 可传 None = 全量）
        add_tag: "JAV" / "Non-JAV" / None —— 自动打对应语言标签
        set_stash_id: True 时写 stash_ids（JAV 用 remote_site_id）

    Returns:
        True=成功（或无需变更）/ False=失败
    """
    inp: dict = {"id": str(scene_id)}

    # ---- 基础字段 ----
    for field in ("title", "code", "date", "director", "details"):
        val = scraped_data.get(field)
        if val:
            inp[field] = val

    # ---- 封面 ----
    cover_image = scraped_data.get("image")
    if cover_image:
        inp["cover_image"] = cover_image

    # ---- 片商 ----
    scraped_studio = scraped_data.get("studio")
    if scraped_studio:
        if scraped_studio.get("stored_id"):
            inp["studio_id"] = scraped_studio["stored_id"]
        elif scraped_studio.get("name"):
            studio_id = await studio_mod.create_or_find_studio(
                client, scraped_studio, stash_box_index
            )
            if studio_id:
                inp["studio_id"] = studio_id

    # ---- 演员（保留当前 + 增量；box 双源数据统一走 create_or_find_performer，含更新）----
    scraped_performers = scraped_data.get("performers", [])
    current_info = current_scene_info or {}
    current_performers = current_info.get("performers", [])
    performer_ids = [p["id"] for p in current_performers if p.get("id")]
    for p in scraped_performers:
        if not p.get("name"):
            continue
        # 统一走 create_or_find_performer：按 stash_id/名称匹配 → 已存在则全字段更新（补多源 stash_ids）
        pid = await performer_mod.create_or_find_performer(client, p, stash_box_index)
        if pid and pid not in performer_ids:
            performer_ids.append(pid)
    if performer_ids:
        inp["performer_ids"] = performer_ids

    # ---- 标签（compare_tags 差集，只加不删 + add_tag）----
    scraped_tags = scraped_data.get("tags", [])
    current_tags = current_info.get("tags", [])
    tag_ids = await _resolve_tag_ids(client, current_tags, scraped_tags, add_tag)
    if tag_ids:
        inp["tag_ids"] = tag_ids

    # ---- stash_id（多源：box 合并数据可能直接带 stash_ids；JAV 用 set_stash_id 单源）----
    box_stash_ids = scraped_data.get("stash_ids") or []
    if box_stash_ids:
        # 合并已有的 stash_ids（box 已处理好多源合并）
        inp["stash_ids"] = box_stash_ids
    elif set_stash_id:
        remote_site_id = scraped_data.get("remote_site_id")
        if remote_site_id:
            endpoint = await client.get_endpoint(stash_box_index)
            inp["stash_ids"] = [{"endpoint": endpoint, "stash_id": remote_site_id}]

    # ---- urls（JAV 刮削数据有）----
    urls = scraped_data.get("urls") or []
    if urls:
        inp["urls"] = urls

    # ---- 提交（剔除空值）----
    inp = {k: v for k, v in inp.items() if v is not None and v != [] and v != {} and v != ""}
    if len(inp) == 1:
        logger.info("         - ⏭️ 无任何变更，跳过更新")
        return True

    result = await scene_mod.update_scene(client, inp)
    if result:
        return True

    # ── 外键约束失败自动重试（方案 A：标签缓存过期兜底）────
    # 场景写入失败 + 报错含 FOREIGN KEY constraint failed = tag_ids 里有 Stash 侧
    # 已不存在的标签 id（_tag_cache 过期，未感知外部的标签删除/合并）。
    # 处理：失效标签缓存 → 用最新全量标签重新解析 tag_ids → 重试一次。
    errors = getattr(client, "last_errors", None) or []
    if any(_FK_ERROR_MARK in str(e.get("message", "")) for e in errors):
        logger.warning(
            "         - ⚠️ 外键约束失败（疑似标签缓存过期），失效缓存并重试一次 | 场景=%s",
            scene_id,
        )
        tag_mod.invalidate_cache()
        retry_tag_ids = await _resolve_tag_ids(
            client, current_tags, scraped_tags, add_tag
        )
        if retry_tag_ids:
            inp["tag_ids"] = retry_tag_ids
        else:
            inp.pop("tag_ids", None)
        return await scene_mod.update_scene(client, inp)

    return False
