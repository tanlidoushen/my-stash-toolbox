"""JavDB Search —— 格式化 / 展示（搜索结果、详情、磁力链接、Stash 查询）。
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


# ═══════════════════════════ 搜索结果 ═══════════════════════════

def _format_search_caption(code, movies, total):
    """格式化搜索结果列表文本。"""
    lines = [f"🔍 <b>搜索结果: {code}</b>", ""]
    if not movies:
        lines.append("未找到匹配结果。")
        return "\n".join(lines)

    for idx, m in enumerate(movies, 1):
        number = m.get("number") or "???"
        title = (m.get("title") or "").strip()
        date = m.get("release_date") or ""
        date_str = f" [{date}]" if date else ""
        if len(title) > 50:
            title = title[:47] + "..."
        lines.append(f"{idx}. <b>{number}</b> {title}{date_str}")

    if total > len(movies):
        lines.append(f"\n… 共 {total} 个结果")

    return "\n".join(lines)


def _build_search_buttons(movies):
    """为搜索结果生成内联按钮。"""
    buttons = []
    row = []
    for idx, m in enumerate(movies, 1):
        row.append(InlineKeyboardButton(
            str(idx), callback_data=f"javdb_pick_{m['id']}"
        ))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


# ═══════════════════════════ 元数据（共用） ═══════════════════════════

def _format_metadata(movie, stash_map=None):
    """格式化影片基本元数据（标题、番号、日期、片商、演员、标签、摘要）→ 文本行列表。

    排版对齐 notify/builder.py 的入库通知模板：
    - 字段名 <b>加粗</b>（如 <b>番号:</b>）
    - 番号用 <code>code</code> 样式
    - 演员分 ♀️女优 / ♂️男优 两行
    - 标签带 # 前缀 + Stash 超链接
    - 片商超链接

    被 _format_detail 和 _format_detail_with_buttons 共用，消除约 70 行重复。
    """
    stash = stash_map or {}
    base = stash.get("base_url", "")
    lines = []

    title = (movie.get("title") or "").strip()
    number = movie.get("number") or ""
    date = movie.get("release_date") or ""
    duration = movie.get("duration") or 0
    summary = (movie.get("summary") or "").strip()

    lines.append(f"📝 <b>标题:</b> {title}" if title else "📝 <b>标题:</b> (无标题)")

    # ── 番号（查 Stash 场景，对齐通知模板：<b>番号:</b> <code>xxx</code>） ──
    if number:
        scene_id = stash.get("scene_id")
        if scene_id:
            lines.append(f'📀 <b>番号:</b> <a href="{base}/scenes/{scene_id}"><code>{number}</code></a>')
        else:
            lines.append(f"📀 <b>番号:</b> <code>{number}</code>")

    if date:
        lines.append(f"📅 <b>发行日期:</b> {date}")
    if duration:
        lines.append(f"⏱ <b>时长:</b> {duration} 分钟")

    # ── 片商 ──
    maker = (movie.get("maker_name") or "").strip()
    if maker:
        studio_id = stash.get("studio_id")
        if studio_id:
            lines.append(f'🏢 <b>片商:</b> <a href="{base}/studios/{studio_id}">#{maker.replace(" ", "_")}</a>')
        else:
            lines.append(f"🏢 <b>片商:</b> #{maker.replace(' ', '_')}")

    # ── 演员（分女优/男优两行，对齐通知模板） ──
    actors = movie.get("actors") or []
    if actors:
        perf_map = stash.get("performers") or {}
        female_parts = []
        male_parts = []
        for a in actors:
            name = (a.get("name") or "").strip()
            if not name:
                continue
            gender = a.get("gender")
            tag_text = "#%s" % name.replace(" ", "_")
            pid = perf_map.get(name)
            if pid:
                formatted = f'<a href="{base}/performers/{pid}">{tag_text}</a>'
            else:
                formatted = tag_text
            if gender == 1:
                male_parts.append(formatted)
            else:
                female_parts.append(formatted)
        if female_parts:
            lines.append(f"♀️ <b>女优:</b> {' '.join(female_parts)}")
        if male_parts:
            lines.append(f"♂️ <b>男优:</b> {' '.join(male_parts)}")

    # ── 标签（#前缀 + Stash 超链接，对齐通知模板） ──
    tags = movie.get("tags") or []
    if tags:
        tag_map = stash.get("tags") or {}
        tag_parts = []
        for t in tags[:10]:
            name = (t.get("name") or "").strip()
            if not name:
                continue
            tag_text = "#%s" % name.replace(" ", "_")
            tid = tag_map.get(name)
            if tid:
                tag_parts.append(f'<a href="{base}/tags/{tid}">{tag_text}</a>')
            else:
                tag_parts.append(tag_text)
        if tag_parts:
            lines.append(f"🏷️ <b>标签:</b> {' '.join(tag_parts)}")

    if summary:
        if len(summary) > 200:
            summary = summary[:197] + "..."
        lines.append("")
        lines.append(f"📖 <b>简介:</b> <blockquote expandable>{summary}</blockquote>")

    return lines


# ═══════════════════════════ 磁力链接 ═══════════════════════════

def _build_stash_link(stash_map=None) -> str:
    """本地 Stash 已有该番号 → 生成"查看原视频"链接行（对齐 notify/builder.py 模板）。

    返回空串 = 本地没有该场景。场景按 code 精确匹配（_stash_lookup 已查）。
    """
    stash = stash_map or {}
    scene_id = stash.get("scene_id")
    base = (stash.get("base_url") or "").rstrip("/")
    if scene_id and base:
        return '✅ <b>本地已有</b> · ▶️ <a href="%s/scenes/%s">查看原视频</a>' % (base, scene_id)
    return ""


def _format_magnets(magnets, movie_id=None, page=0, page_size=8):
    """格式化磁力链接列表（分页），返回 (text, sorted_magnets, reply_markup)。

    接受 MagnetInfo 对象列表。排序：来源优先级 → 中字 → 高清 → 大小降序
    （由 MagnetInfo 所在源的 sort_key 决定，已在管理器 search_all 中排好；
     此处做兜底二次排序）。
    """
    if not magnets:
        return "", [], None

    # 来源体系组序 / 标签子组序（从 Config 读，支持环境变量覆盖）
    from config import Config
    _GROUP_ORDER = [g.strip() for g in
                    getattr(Config, "MAGNET_GROUP_ORDER", "AVDB,JavDB").split(",") if g.strip()]
    _TAG_PRIORITY = [t.strip() for t in
                     getattr(Config, "MAGNET_TAG_PRIORITY", "中字,4K,高清").split(",") if t.strip()]
    _GROUP_ICONS = {"AVDB": "🌸", "JavDB": "🗾"}

    def _source_group(m):
        """磁力 → 来源体系组名。AVDB 系(色花堂/x1080x)→'AVDB';JavDB→'JavDB';其余按 source 原文。"""
        src = (m.source or "").strip()
        if src in ("色花堂", "x1080x") or "AVDB" in src:
            return "AVDB"
        if src == "JavDB":
            return "JavDB"
        return src or "其他"

    def _tag_group(m):
        """磁力 → 标签子组。按 MAGNET_TAG_PRIORITY 首个匹配标签归类，无匹配→'其他'。"""
        tags = m.tags or []
        for t in _TAG_PRIORITY:
            if t in tags:
                return t
        return "其他"

    # ── 排序：来源组序 → 标签子组序 → 组内(中字/高清/大小)；关闭分组时仅组内规则 ──
    def _sort_key(m):
        if not getattr(Config, "MAGNET_GROUPING_ENABLED", True):
            cnsub = "中字" in (m.tags or [])
            hd = "高清" in (m.tags or [])
            return (0 if cnsub else 1, 0 if hd else 1, -(m.size_mb or 0))
        g = _source_group(m)
        tg = _tag_group(m)
        gi = _GROUP_ORDER.index(g) if g in _GROUP_ORDER else len(_GROUP_ORDER)
        ti = _TAG_PRIORITY.index(tg) if tg in _TAG_PRIORITY else len(_TAG_PRIORITY)
        cnsub = "中字" in (m.tags or [])
        hd = "高清" in (m.tags or [])
        return (gi, ti, 0 if cnsub else 1, 0 if hd else 1, -(m.size_mb or 0))

    sorted_magnets = sorted(magnets, key=_sort_key)
    total = len(sorted_magnets)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    end = min(start + page_size, total)
    page_magnets = sorted_magnets[start:end]

    text_lines = [
        "🧲 <b>磁力链接</b> (共 %d 条 | 第%d/共%d页)" % (total, page + 1, total_pages),
        "",
    ]

    def _fmt_one(m):
        title = (m.title or "未命名").strip()
        if len(title) > 50:
            title = title[:47] + "..."
        size_str = m.fmt_size()
        tags = m.tags or []
        # 中字/高清/4K/破解 等作为重点标签，其余（如站点名 x1080x/色花堂）作为来源
        badges = [t for t in tags if t in ("中字", "高清", "4K", "破解", "无码", "免费", "UC")]
        srcs = [t for t in tags if t not in ("中字", "高清", "4K", "破解", "无码", "免费", "UC")]
        parts = [size_str]
        if badges:
            parts.append(" · ".join(badges))
        if srcs:
            parts.append("🖥" + "/".join(srcs))
        return title, parts

    # ── 渲染：分组标题(来源体系→标签子组) + 条目 + 按钮 ──
    grouping = getattr(Config, "MAGNET_GROUPING_ENABLED", True)
    btn_rows = []
    btn_row = []
    last_group = None
    last_tag = None
    for i, m in enumerate(page_magnets):
        global_idx = start + i
        g = _source_group(m)
        tg = _tag_group(m)
        # 来源体系组标题
        if grouping and g != last_group:
            count = sum(1 for x in page_magnets if _source_group(x) == g)
            icon = _GROUP_ICONS.get(g, "📦")
            text_lines.append("")
            text_lines.append("%s %s (%d)" % (icon, g, count))
            last_group = g
            last_tag = None
        # 标签子组标题
        if grouping and tg != last_tag:
            text_lines.append("  ─ %s" % tg)
            last_tag = tg
        title, info_parts = _fmt_one(m)
        text_lines.append("  %d. %s [%s]" % (global_idx + 1, title, ", ".join(info_parts)))
        if movie_id:
            cb = "mag_add_%s_%d" % (movie_id, global_idx)
            btn_row.append(InlineKeyboardButton(str(global_idx + 1), callback_data=cb))
            if len(btn_row) == 4:
                btn_rows.append(btn_row)
                btn_row = []
    if btn_row:
        btn_rows.append(btn_row)

    # Page navigation buttons
    if total_pages > 1 and movie_id:
        page_btns = []
        for p in range(total_pages):
            label = "页%d" % (p + 1)
            if p == page:
                label = "《" + label + "》"
            page_btns.append(InlineKeyboardButton(label, callback_data="mag_page_%s_%d" % (movie_id, p)))
        btn_rows.append(page_btns)

    text = "\n".join(text_lines)
    markup = InlineKeyboardMarkup(btn_rows) if btn_rows else None
    return text, sorted_magnets, markup


# ═══════════════════════════ 完整详情 ═══════════════════════════

def _format_detail(movie, magnets=None, stash_map=None):
    """格式化单个影片详情文本（含磁力链接、Stash 超链接）。"""
    lines = _format_metadata(movie, stash_map)

    # ── 磁力链接（仅文本，无按钮） ──
    if magnets:
        magnet_text, _sorted_mag, _mag_btn = _format_magnets(
            magnets, movie_id=(movie.get("id") or "")
        )
        if magnet_text:
            lines.append("")
            lines.append(magnet_text)

    vid = movie.get("id") or ""
    if vid:
        lines.append("")
        lines.append(f'🔗 <a href="https://javdb.com/v/{vid}">在 JavDB 查看</a>')

    return "\n".join(lines)


def _format_detail_with_buttons(movie, magnets=None, stash_map=None, page=0):
    """返回 (text, sorted_magnets, reply_markup) 供 handle_javdb_detail 使用。

    本地已有该番号时，"✅ 本地已有 · ▶️ 查看原视频"链接行渲染在消息最顶部
    （对齐 notify/builder.py 入库通知模板的"查看原视频"位置）。
    """
    stash_link = _build_stash_link(stash_map)
    lines = []
    if stash_link:
        lines.append(stash_link)
        lines.append("")
    lines.extend(_format_metadata(movie, stash_map))
    movie_id = movie.get("id") or ""

    sorted_magnets = []
    magnet_markup = None
    if magnets:
        magnet_text, sorted_magnets, magnet_markup = _format_magnets(
            magnets, movie_id=movie_id, page=page,
        )
        if magnet_text:
            lines.append("")
            lines.append(magnet_text)

    vid = movie.get("id") or ""
    if vid:
        lines.append("")
        lines.append(f'🔗 <a href="https://javdb.com/v/{vid}">在 JavDB 查看</a>')

    text = "\n".join(lines)
    return text, sorted_magnets, magnet_markup


# ═══════════════════════════ Stash 查询 ═══════════════════════════

async def _stash_lookup(movie):
    """在 Stash 中全量查询演员/标签（含别名匹配），返回超链接映射。"""
    from stash.client import StashClient
    from stash import query as Q
    from config import Config

    result = {"base_url": Config.STASH_BASE_URL.rstrip("/")}
    client = StashClient(Config.STASH_URL, api_key=Config.STASH_APIKEY)

    # ── 场景（按 code 精确匹配） ──
    code = (movie.get("number") or "").strip()
    if code:
        try:
            data = await client.post(Q.FIND_SCENES_BY_CODE, {
                "filter": {"code": {"value": code, "modifier": "EQUALS"}}
            })
            scenes = (data.get("findScenes") or {}).get("scenes") or []
            result["scene_id"] = scenes[0]["id"] if scenes else None
        except Exception:
            result["scene_id"] = None
    else:
        result["scene_id"] = None

    # ── 全量演员 → 构建 name/alias → id 字典 ──
    perf_lookup = {}
    try:
        data = await client.post(Q.FIND_PERFORMERS, {"filter": {"per_page": -1}})
        performers = (data.get("findPerformers") or {}).get("performers") or []
        for p in performers:
            pid = p["id"]
            perf_lookup[p.get("name", "")] = pid
            for alias in (p.get("alias_list") or []):
                if alias:
                    perf_lookup[alias] = pid
    except Exception:
        pass

    perf_map = {}
    for p in (movie.get("actors") or []):
        name = (p.get("name") or "").strip()
        if name:
            perf_map[name] = perf_lookup.get(name)
    result["performers"] = perf_map

    # ── 全量标签 → 构建 name/alias → id 字典 ──
    tag_lookup = {}
    try:
        data = await client.post(Q.FIND_TAGS, {"filter": {"per_page": -1}})
        tags_list = (data.get("findTags") or {}).get("tags") or []
        for t in tags_list:
            tid = t["id"]
            tag_lookup[t.get("name", "")] = tid
            for alias in (t.get("aliases") or []):
                if alias:
                    tag_lookup[alias] = tid
    except Exception:
        pass

    tag_map = {}
    for t in (movie.get("tags") or []):
        name = (t.get("name") or "").strip()
        if name:
            tag_map[name] = tag_lookup.get(name)
    result["tags"] = tag_map

    # ── 片商 ──
    maker = (movie.get("maker_name") or "").strip()
    if maker:
        try:
            data = await client.post(Q.FIND_STUDIOS, {"filter": {"q": maker}})
            studios = (data.get("findStudios") or {}).get("studios") or []
            result["studio_id"] = studios[0]["id"] if studios else None
        except Exception:
            result["studio_id"] = None
    else:
        result["studio_id"] = None

    return result