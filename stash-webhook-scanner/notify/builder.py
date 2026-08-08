"""TG 消息构建器 —— 纯数据到格式化 HTML 字符串。"""

import logging

from stash import query as Q

logger = logging.getLogger(__name__)


def format_tag(name):
    """清理名字，去首尾空格并将中间空格替换为下划线，返回带#的标签。"""
    if not name:
        return ""
    clean_name = name.strip().replace(" ", "_")
    return "#%s" % clean_name


async def get_scene_data(client, scene_id):
    """从 Stash 查询指定场景的详细信息（用于通知）。"""
    data = await client.post(Q.SCENE_FOR_NOTIFICATION, {"id": str(scene_id)})
    if data:
        return data.get("findScene")
    return None


async def build_caption(scene, is_japanese, client, stash_base_url, title_prefix="🎬 <b>影片处理完成</b>"):
    """根据场景数据和区域类型构建 HTML 消息文本。

    title_prefix: 消息标题行，调用方可自定义（如 "🗑️ <b>确认删除场景？</b>"）。
    """
    lines = ["%s\n" % title_prefix]

    scene_id = scene.get("id")

    # 点击播放
    if scene_id and stash_base_url:
        play_url = "%s/scenes/%s" % (stash_base_url, scene_id)
        lines.append('▶️ <a href="%s">点击播放</a>' % play_url)

    # 制作地区
    if is_japanese:
        from stash.tag import create_or_find_tag
        jav_tag_id = await create_or_find_tag(client, "JAV", verbose=False)
        if jav_tag_id:
            jav_tag_url = "%s/tags/%s" % (stash_base_url.rstrip("/"), jav_tag_id)
            lines.append('🌐 <b>制作地区:</b> <a href="%s">#JAV</a>' % jav_tag_url)
        else:
            lines.append("🌐 <b>制作地区:</b> #JAV")
    else:
        from stash.tag import create_or_find_tag
        non_jav_tag_id = await create_or_find_tag(client, "Non-JAV", verbose=False)
        if non_jav_tag_id:
            non_jav_tag_url = "%s/tags/%s" % (stash_base_url.rstrip("/"), non_jav_tag_id)
            lines.append('🌐 <b>制作地区:</b> <a href="%s">#Non-JAV</a>' % non_jav_tag_url)
        else:
            lines.append("🌐 <b>制作地区:</b> #Non-JAV")

    # 标题
    title = scene.get("title")
    if title:
        lines.append("📝 <b>标题:</b> %s" % title)

    # 番号
    code = scene.get("code")
    if code:
        label = "番号" if is_japanese else "工作室代码"
        lines.append('📀 <b>%s:</b> <code>%s</code>' % (label, code))

    # 女优 / 男优
    female_actors = []
    male_actors = []
    for p in scene.get("performers", []):
        actor_id = p.get("id")
        name = p.get("name", "")
        gender = p.get("gender")
        tag_text = format_tag(name)
        if not tag_text:
            continue
        if actor_id and stash_base_url:
            actor_url = "%s/performers/%s" % (stash_base_url, actor_id)
            formatted_actor = '<a href="%s">%s</a>' % (actor_url, tag_text)
        else:
            formatted_actor = tag_text
        if gender and gender.upper() == "MALE":
            male_actors.append(formatted_actor)
        else:
            female_actors.append(formatted_actor)

    if female_actors:
        lines.append("♀️ <b>女优:</b> %s" % " ".join(female_actors))
    if male_actors:
        lines.append("♂️ <b>男优:</b> %s" % " ".join(male_actors))

    # 发行日期
    release_date = scene.get("date")
    if release_date:
        lines.append("📅 <b>发行日期:</b> %s" % release_date)

    # 片商 / 工作室
    studio = scene.get("studio")
    if studio:
        studio_id = studio.get("id")
        studio_name = studio.get("name")
        if studio_name:
            tag_text = format_tag(studio_name)
            if studio_id and stash_base_url:
                studio_url = "%s/studios/%s" % (stash_base_url, studio_id)
                studio_line = '<a href="%s">%s</a>' % (studio_url, tag_text)
            else:
                studio_line = tag_text
            label = "片商" if is_japanese else "工作室"
            lines.append("🏢 <b>%s:</b> %s" % (label, studio_line))

    # 文件信息
    files = scene.get("files", [])
    if files and len(files) > 0:
        file_info = files[0]
        size_bytes = file_info.get("size", 0)
        if size_bytes:
            size_gb = round(size_bytes / (1024 ** 3), 2)
            lines.append("💾 <b>大小:</b> %s GB" % size_gb)
        duration = file_info.get("duration")
        if duration:
            duration_min = int(duration // 60)
            lines.append("⏱ <b>时长:</b> %d 分钟" % duration_min)

    # 简介
    details = scene.get("details")
    if details:
        MAX_CAPTION_LEN = 1024
        current = "\n".join(lines)
        prefix = "📖 <b>简介:</b> <blockquote expandable>"
        suffix = "</blockquote>"
        available = MAX_CAPTION_LEN - len(current) - 1 - len(prefix) - len(suffix)
        if available <= 0:
            pass
        elif len(details) > available:
            lines.append("%s%s...%s" % (prefix, details[: available - 3], suffix))
        else:
            lines.append("%s%s%s" % (prefix, details, suffix))

    # 标签
    tags_list = []
    for t in scene.get("tags", []):
        tag_id = t.get("id")
        tag_name = t.get("name")
        if not tag_name:
            continue
        tag_text = format_tag(tag_name)
        if tag_id and stash_base_url:
            tag_url = "%s/tags/%s" % (stash_base_url, tag_id)
            tags_list.append('<a href="%s">%s</a>' % (tag_url, tag_text))
        else:
            tags_list.append(tag_text)
    if tags_list:
        lines.append("\n🏷️ <b>标签:</b> %s" % " ".join(tags_list))

    return "\n".join(lines)

