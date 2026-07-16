import logging
import time
import requests

logger = logging.getLogger(__name__)


def get_stash_boxes(stash_url):
    """查询 Stash 配置中的 stash-box 列表（按顺序返回 endpoint 列表）。"""
    query = """
    query GetStashBoxesOrder {
      configuration {
        general {
          stashBoxes { name endpoint }
        }
      }
    }
    """
    data = _post(stash_url, query, {})
    if data:
        boxes = data.get('configuration', {}).get('general', {}).get('stashBoxes', [])
        return [b['endpoint'] for b in boxes]
    return []



def _post(stash_url, query, variables):
    """发送 GraphQL 请求，返回 data 或 None。"""
    try:
        resp = requests.post(
            stash_url,
            json={"query": query, "variables": variables},
            headers={"Content-Type": "application/json"},
            timeout=120,
        )
        data = resp.json()
        if "errors" in data:
            logger.error("❌ GraphQL 错误：%s", data["errors"])
            return None
        return data.get("data")
    except Exception as e:
        logger.error("❌ 请求异常：%s", e)
        return None


def _scan(stash_url, scan_paths, extra_vars=None):
    """执行 Stash 的 metadataScan GraphQL 请求。"""
    query = """
    mutation MetadataScan($input: ScanMetadataInput!) {
      metadataScan(input: $input)
    }
    """
    variables = {"input": {"paths": scan_paths}}
    if extra_vars:
        variables["input"].update(extra_vars)

    data = _post(stash_url, query, variables)
    if data is None:
        return None
    job_id = data["metadataScan"]
    logger.info("      └─ 🚀 扫描任务已提交 | 任务ID=%s", job_id)
    return job_id


def scan_simple(stash_url, scan_paths):
    """简单扫描（仅路径）。"""
    return _scan(stash_url, scan_paths)


def scan_detailed(stash_url, scan_paths):
    """详细扫描（仅重新入库，不生成预览/指纹/缩略图等）。"""
    return _scan(stash_url, scan_paths, {
        "rescan": True,
    })


def get_job_status(stash_url, job_id):
    """查询任务状态。返回状态字典或 None。"""
    query = """
    query FindJob($input: FindJobInput!) {
      findJob(input: $input) {
        id
        status
        progress
        description
        startTime
        endTime
        error
      }
    }
    """
    variables = {"input": {"id": str(job_id)}}
    data = _post(stash_url, query, variables)
    if data is None:
        return None
    return data["findJob"]


def wait_for_job(stash_url, job_id, poll_interval=3):
    """无限等待任务完成，直到结束或失败，返回最终状态字典。"""
    logger.info("         ├─ ⏳ 等待任务 %s 完成...", job_id)
    while True:
        status = get_job_status(stash_url, job_id)
        if status is None:
            logger.warning("         ├─ ⚠️ 查询任务 %s 状态失败，稍后重试", job_id)
            time.sleep(poll_interval)
            continue

        s = status["status"]
        p = status.get("progress")
        logger.info("         ├─ 📊 任务 %s | 状态=%s | 进度=%s", job_id, s, p)

        if s == "FINISHED":
            logger.info("         └─ ✅ 任务 %s 已完成！", job_id)
            return status
        if s in ("FAILED", "CANCELLED"):
            err = status.get("error", "未知")
            logger.warning("         └─ ❌ 任务 %s 已结束（%s）：%s", job_id, s, err)
            return status

        time.sleep(poll_interval)


def wait_for_job_running(stash_url, job_id, poll_interval=3):
    """等待任务开始运行（状态不再是 READY），返回当前状态字典。"""
    logger.info("         ├─ ⏳ 等待任务 %s 开始运行...", job_id)
    while True:
        status = get_job_status(stash_url, job_id)
        if status is None:
            logger.warning("         ├─ ⚠️ 查询任务 %s 状态失败，稍后重试", job_id)
            time.sleep(poll_interval)
            continue

        s = status["status"]
        p = status.get("progress")
        logger.info("         ├─ 📊 任务 %s | 状态=%s | 进度=%s", job_id, s, p)

        if s in ("RUNNING", "FINISHED"):
            logger.info("         └─ ✅ 任务 %s 已开始运行", job_id)
            return status
        if s in ("FAILED", "CANCELLED"):
            err = status.get("error", "未知")
            logger.warning("         └─ ❌ 任务 %s 已结束（%s）：%s", job_id, s, err)
            return status

        time.sleep(poll_interval)



def find_scenes_by_path(stash_url, path):
    """根据文件路径查询场景。返回场景 ID 列表。"""
    query = """
    query FindSceneByPath($filter: SceneFilterType!) {
      findScenes(scene_filter: $filter) {
        count
        scenes {
          id
          files { path }
        }
      }
    }
    """
    variables = {
        "filter": {
            "path": { "value": path, "modifier": "EQUALS" }
        }
    }
    data = _post(stash_url, query, variables)
    if data is None:
        return []
    scenes = data["findScenes"]["scenes"]
    logger.info("      └─ ✅ 找到 %d 个场景", len(scenes))
    return [s["id"] for s in scenes]



def get_scene_stash_id(stash_url, scene_id, endpoint="https://stashdb.org/graphql"):
    """查询场景的 stash_id（指定 endpoint）。返回 stash_id 或 None。"""
    query = """
    query FindScene($id: ID!) {
      findScene(id: $id) {
        id
        stash_ids {
          endpoint
          stash_id
        }
      }
    }
    """
    variables = {"id": str(scene_id)}
    data = _post(stash_url, query, variables)
    if data is None:
        return None
    scene = data.get("findScene")
    if not scene:
        return None
    for si in scene.get("stash_ids", []):
        if si["endpoint"] == endpoint:
            return si["stash_id"]
    return None



def get_scene_info(stash_url, scene_id):
    """获取当前场景的完整信息（工作室、演员、标签、stash_ids）。"""
    query = """
    query GetScene($id: ID!) {
      findScene(id: $id) {
        id
        title
        code
        stash_ids { endpoint stash_id }
        studio { id name }
        performers { id name stash_ids { endpoint stash_id } }
        tags { id name }
      }
    }
    """
    variables = {"id": str(scene_id)}
    data = _post(stash_url, query, variables)
    if data is None:
        return None
    return data.get("findScene")



def resolve_stash_box_index(stash_url, scene_id, default=0):
    """根据场景已有的 stash_ids 自动解析 stash-box index。"""
    info = get_scene_info(stash_url, scene_id)
    if not info:
        return default
    stash_ids = info.get('stash_ids', [])
    if not stash_ids:
        return default
    # 取第一个 stash_id 的 endpoint 去配置列表中找对应下标
    endpoint = stash_ids[0]['endpoint']
    boxes = get_stash_boxes(stash_url)
    for i, ep in enumerate(boxes):
        if ep == endpoint:
            return i
    return default



def scrape_scene(stash_url, scene_id, stash_box_index=0):
    """使用 Stash-box metadataIdentify 进行刮削。返回 job_id 或 None。"""
    query = """
    mutation StartFallbackIdentify {
      metadataIdentify(
        input: {
          sources: [
            {
              source: { stash_box_index: IDX }
              options: {
                includeMalePerformers: true
                setCoverImage: true
                setOrganized: true
                skipMultipleMatches: false
                fieldOptions: [
                  { field: "TITLE", strategy: OVERWRITE }
                  { field: "STUDIO", strategy: MERGE, createMissing: true }
                  { field: "DATE", strategy: MERGE }
                  { field: "DETAILS", strategy: MERGE }
                  { field: "URLS", strategy: MERGE }
                  { field: "PERFORMERS", strategy: MERGE, createMissing: true }
                  { field: "TAGS", strategy: MERGE, createMissing: true }
                  { field: "STUDIO_CODE", strategy: MERGE }
                  { field: "DIRECTOR", strategy: MERGE }
                  { field: "STASH_IDS", strategy: MERGE }
                ]
              }
            }
          ]
          sceneIDs: ["SID"]
        }
      )
    }
    """.replace("IDX", str(stash_box_index)).replace("SID", str(scene_id))

    data = _post(stash_url, query, {})
    if data is None:
        return None
    job_id = data.get("metadataIdentify")
    logger.info("         └─ 🚀 刮削任务已提交 | 场景 %s | 任务ID=%s", scene_id, job_id)
    return job_id



def _get_endpoint(stash_url, stash_box_index=0):
    """根据 index 从服务器配置获取 stash-box endpoint。"""
    boxes = get_stash_boxes(stash_url)
    if stash_box_index < len(boxes):
        return boxes[stash_box_index]
    return "https://stashdb.org/graphql"


def scrape_scene_by_remote_id(stash_url, scene_id, stash_id, stash_box_index=0):
    """使用 stash-box scrapeSingleScene 根据远程 stash_id 重新刮削场景完整元数据。"""
    endpoint = _get_endpoint(stash_url, stash_box_index)
    query = """
    query ScrapeSingleScene($source: ScraperSourceInput!, $input: ScrapeSingleSceneInput!) {
      scrapeSingleScene(source: $source, input: $input) {
        title code details director urls date remote_site_id
        studio {
          stored_id name url
          parent { stored_id name url parent { stored_id name url } }
          image remote_site_id
        }
        performers {
          stored_id images name gender urls birthdate country
          height measurements aliases remote_site_id
        }
        tags { name }
      }
    }
    """
    variables = {
        "source": {"stash_box_endpoint": endpoint},
        "input": {
            "scene_id": str(scene_id),
            "scene_input": {"remote_site_id": stash_id},
        },
    }
    data = _post(stash_url, query, variables)
    if data is None:
        return None
    scraped = data.get("scrapeSingleScene")
    if not scraped:
        return None
    # 处理返回可能是列表的情况
    if isinstance(scraped, list):
        if not scraped:
            logger.warning("         ⚠️ 场景 %s 通过 stash_id=%s 刮削无结果", scene_id, stash_id)
            return None
        for item in scraped:
            if item.get("remote_site_id") == stash_id:
                return item
        logger.warning("         ⚠️ 场景 %s 未找到完全匹配，使用第一个结果", scene_id)
        return scraped[0]
    return scraped



def get_tag_with_aliases(stash_url, tag_name):
    """根据名称查找标签（含别名匹配）。"""
    query = """
    query FindTags($filter: FindFilterType) {
      findTags(filter: $filter) {
        tags { id name aliases }
      }
    }
    """
    variables = {"filter": {"q": tag_name, "per_page": -1}}
    data = _post(stash_url, query, variables)
    if not data:
        return None
    tags = data.get("findTags", {}).get("tags", [])
    for t in tags:
        if t["name"].lower() == tag_name.lower():
            return t
    for t in tags:
        for alias in t.get("aliases", []):
            if alias.lower() == tag_name.lower():
                return t
    return None


def create_or_find_tag(stash_url, tag_name):
    """查找或创建标签。"""
    existing = get_tag_with_aliases(stash_url, tag_name)
    if existing:
        logger.info("         🏷️ 标签已存在: %s -> %s", tag_name, existing["name"])
        return existing["id"]
    query = """
    mutation CreateTag($input: TagCreateInput!) {
      tagCreate(input: $input) { id name }
    }
    """
    data = _post(stash_url, query, {"input": {"name": tag_name}})
    if data and data.get("tagCreate"):
        tid = data["tagCreate"]["id"]
        logger.info("         🏷️ 创建新标签: %s", tag_name)
        return tid
    logger.warning("         ⚠️ 创建标签失败: %s", tag_name)
    return None


def get_all_tags_with_aliases(stash_url):
    """获取全部标签及其别名。"""
    query = """
    query FindTags($filter: FindFilterType) {
      findTags(filter: $filter) {
        tags { id name aliases }
      }
    }
    """
    data = _post(stash_url, query, {"filter": {"per_page": -1}})
    if data:
        return data.get("findTags", {}).get("tags", [])
    return []


def normalize_tag_name(tag_name, all_tags):
    """将标签名标准化为规范名称（考虑别名）。"""
    lower = tag_name.lower()
    for t in all_tags:
        if t["name"].lower() == lower:
            return t["name"]
        for alias in t.get("aliases", []):
            if alias.lower() == lower:
                return t["name"]
    return tag_name


def compare_tags(stash_url, current_tags, scraped_tags):
    """
    比较当前标签和刮削标签。
    返回: (need_update, reason, merged_tag_names)
    """
    current_tags = current_tags or []
    scraped_tags = scraped_tags or []
    all_tags = get_all_tags_with_aliases(stash_url)

    current_norm = {normalize_tag_name(t["name"], all_tags) for t in current_tags}
    scraped_norm = {normalize_tag_name(t["name"], all_tags) for t in scraped_tags}

    if not current_norm and not scraped_norm:
        return False, '双方无标签', []
    if scraped_norm.issubset(current_norm):
        return False, '刮削标签是当前标签的子集', []

    new_tags = scraped_norm - current_norm
    if new_tags:
        merged = current_norm | scraped_norm
        return True, '发现 %d 个新标签' % len(new_tags), list(merged)
    return False, '无变化', []



def find_studio_by_name(stash_url, studio_name):
    """根据名称查找工作室。"""
    query = """
    query FindStudios($filter: FindFilterType, $studio_filter: StudioFilterType) {
      findStudios(filter: $filter, studio_filter: $studio_filter) {
        count
        studios { id name }
      }
    }
    """
    variables = {
        "filter": {"q": studio_name, "per_page": 1},
        "studio_filter": {"name": {"value": studio_name, "modifier": "EQUALS"}},
    }
    data = _post(stash_url, query, variables)
    if data and data.get("findStudios", {}).get("count", 0) > 0:
        return data["findStudios"]["studios"][0]["id"]
    return None


def create_or_find_studio(stash_url, studio_data, stash_box_index=0):
    """查找或创建工作室（含父工作室递归创建）。"""
    name = studio_data.get("name")
    if not name:
        return None

    existing_id = find_studio_by_name(stash_url, name)
    if existing_id:
        logger.info("         🏢 工作室已存在: %s", name)
        return existing_id

    endpoint = _get_endpoint(stash_url, stash_box_index)
    inp = {"name": name}
    if studio_data.get("url"):
        inp["url"] = studio_data["url"]
    if studio_data.get("details"):
        inp["details"] = studio_data["details"]
    if studio_data.get("image"):
        inp["image"] = studio_data["image"]
    if studio_data.get("aliases"):
        inp["aliases"] = studio_data["aliases"]
    if studio_data.get("remote_site_id"):
        inp["stash_ids"] = [{"endpoint": endpoint, "stash_id": studio_data["remote_site_id"]}]
    # 递归创建父工作室
    parent = studio_data.get("parent")
    if parent and parent.get("name"):
        parent_id = create_or_find_studio(stash_url, parent, stash_box_index)
        if parent_id:
            inp["parent_id"] = parent_id
            logger.info("         🏢 父工作室: %s", parent["name"])

    inp = {k: v for k, v in inp.items() if v is not None and v != []}
    query = """
    mutation CreateStudio($input: StudioCreateInput!) {
      studioCreate(input: $input) { id name }
    }
    """
    data = _post(stash_url, query, {"input": inp})
    if data and data.get("studioCreate"):
        sid = data["studioCreate"]["id"]
        logger.info("         🏢 创建新工作室: %s", name)
        return sid
    logger.warning("         ⚠️ 创建工作室失败: %s", name)
    return None



def find_performer_by_name(stash_url, performer_name):
    """根据名称查找演员。"""
    query = """
    query FindPerformers($filter: FindFilterType, $performer_filter: PerformerFilterType) {
      findPerformers(filter: $filter, performer_filter: $performer_filter) {
        count
        performers { id name }
      }
    }
    """
    variables = {
        "filter": {"q": performer_name, "per_page": 1},
        "performer_filter": {"name": {"value": performer_name, "modifier": "EQUALS"}},
    }
    data = _post(stash_url, query, variables)
    if data and data.get("findPerformers", {}).get("count", 0) > 0:
        return data["findPerformers"]["performers"][0]["id"]
    return None


def create_or_find_performer(stash_url, performer_data, stash_box_index=0):
    """查找或创建演员。"""
    name = performer_data.get("name")
    if not name:
        return None

    existing_id = find_performer_by_name(stash_url, name)
    if existing_id:
        logger.info("         👤 演员已存在: %s", name)
        return existing_id

    endpoint = _get_endpoint(stash_url, stash_box_index)
    inp = {"name": name}
    for field in ("gender", "birthdate", "country", "height_cm", "measurements"):
        val = performer_data.get(field.replace("_cm", ""))
        if val:
            inp[field] = val
    if performer_data.get("aliases"):
        inp["alias_list"] = performer_data["aliases"]
    if performer_data.get("urls"):
        inp["urls"] = performer_data["urls"]
    images = performer_data.get("images", [])
    if images:
        inp["image"] = images[0]
    if performer_data.get("remote_site_id"):
        inp["stash_ids"] = [{"endpoint": endpoint, "stash_id": performer_data["remote_site_id"]}]

    inp = {k: v for k, v in inp.items() if v is not None and v != []}
    query = """
    mutation CreatePerformer($input: PerformerCreateInput!) {
      performerCreate(input: $input) { id name }
    }
    """
    data = _post(stash_url, query, {"input": inp})
    if data and data.get("performerCreate"):
        pid = data["performerCreate"]["id"]
        logger.info("         👤 创建新演员: %s", name)
        return pid
    logger.warning("         ⚠️ 创建演员失败: %s", name)
    return None



def compare_performers(current_performers, scraped_performers):
    """
    比较当前场景演员和刮削到的演员。
    返回: (need_update, reason)
    """
    current = current_performers or []
    scraped = scraped_performers or []

    if len(current) != len(scraped):
        return True, '演员数量不同 (%d vs %d)' % (len(current), len(scraped))

    if len(current) == 0 and len(scraped) == 0:
        return False, '双方都无演员'

    current_names = {p['name'].lower() for p in current}
    scraped_names = {p.get('name', '').lower() for p in scraped if p.get('name')}
    if current_names == scraped_names:
        return False, '演员名称完全匹配'
    return True, '演员不匹配: %s vs %s' % (current_names, scraped_names)


def compare_studio(current_studio, scraped_studio):
    """
    比较当前场景工作室和刮削到的工作室。
    返回: (need_update, reason)
    """
    cur_name = (current_studio or {}).get('name')
    scr_name = (scraped_studio or {}).get('name')

    if not cur_name and not scr_name:
        return False, '双方都无工作室'
    if not cur_name and scr_name:
        return True, '添加工作室: %s' % scr_name
    if cur_name and not scr_name:
        return True, '移除工作室: %s' % cur_name
    if cur_name.lower() == scr_name.lower():
        return False, '工作室名称匹配'
    return True, '工作室不匹配: %s vs %s' % (cur_name, scr_name)



def update_scene_metadata(stash_url, scene_id, scraped_data, current_scene_info, stash_box_index=0):
    """更新场景的元数据（工作室、演员、标签）。"""
    logger.info("   │   ├─ 📝 更新元数据 | 场景 %s", scene_id)
    inp = {"id": str(scene_id)}

    # ---- 工作室 ----
    studio = scraped_data.get("studio")
    studio_id = None
    if studio:
        if studio.get("stored_id"):
            studio_id = studio["stored_id"]
        elif studio.get("name"):
            studio_id = create_or_find_studio(stash_url, studio, stash_box_index)
    if studio_id:
        inp["studio_id"] = studio_id
        logger.info("   │   ├─ 🏢 工作室: %s", (studio or {}).get("name", "?"))

    # ---- 演员 ----
    performers = scraped_data.get("performers", [])
    performer_ids = []
    for p in performers:
        if not p.get("name"):
            continue
        if p.get("stored_id"):
            performer_ids.append(p["stored_id"])
        else:
            pid = create_or_find_performer(stash_url, p, stash_box_index)
            if pid:
                performer_ids.append(pid)
    if performer_ids:
        inp["performer_ids"] = performer_ids
        logger.info("   │   ├─ 👤 演员: %d 个", len(performer_ids))

    # ---- 标签 ----
    scraped_tags = scraped_data.get("tags", [])
    current_tags = (current_scene_info or {}).get("tags", [])
    need_update_tags, reason, merged_names = compare_tags(stash_url, current_tags, scraped_tags)
    logger.info("   │   ├─ 🏷️ 标签对比: %s", reason)

    if need_update_tags:
        tag_ids = [t['id'] for t in current_tags]
        for tag_name in merged_names:
            all_tags = get_all_tags_with_aliases(stash_url)
            norm_current = {normalize_tag_name(t['name'], all_tags) for t in current_tags}
            if normalize_tag_name(tag_name, all_tags) not in norm_current:
                tid = create_or_find_tag(stash_url, tag_name)
                if tid:
                    tag_ids.append(tid)
        if tag_ids:
            inp["tag_ids"] = tag_ids
            logger.info("   │   └─ 🏷️ 合并后标签总数: %d", len(tag_ids))

    # ---- 提交更新 ----
    if len(inp) == 1:
        logger.info('   │   └─ ⏭️ 无任何变更，跳过更新')
        return True

    mutation = """
    mutation UpdateScene($input: SceneUpdateInput!) {
      sceneUpdate(input: $input) {
        id
        title
        studio { id name }
        performers { id name }
        tags { id name }
      }
    }
    """
    data = _post(stash_url, mutation, {"input": inp})
    if data and data.get("sceneUpdate"):
        updated = data["sceneUpdate"]
        logger.info("   │   └─ ✅ 更新成功 | 场景=%s | 标题=%s | 工作室=%s | 演员=%d | 标签=%d",
                    scene_id, updated.get('title'),
                    (updated.get('studio') or {}).get('name', '无'),
                    len(updated.get('performers', [])),
                    len(updated.get('tags', [])))
        return True
    logger.error("   │   └─ ❌ 场景 %s 元数据更新失败", scene_id)
    if data and "errors" in data:
        logger.error("   │       ❌ GraphQL 错误: %s", data["errors"])
    return False



def enrich_scene_metadata(stash_url, scene_id, stash_id, stash_box_index=0):
    """对已刮削的场景进行元数据补充（演员、工作室、标签）。"""
    logger.info("   ├─ 📝 元数据补充 | 场景 %s | stash_id=%s", scene_id, stash_id)

    # 1. 获取当前场景信息
    current_info = get_scene_info(stash_url, scene_id)
    if not current_info:
        logger.warning('   │   └─ ⚠️ 场景 %s 不存在，跳过', scene_id)
        return False

    # 2. 通过 stash_id 重新刮削完整元数据
    scraped = scrape_scene_by_remote_id(stash_url, scene_id, stash_id, stash_box_index)
    if not scraped:
        logger.warning('   │   └─ ⚠️ 场景 %s 刮削无结果，跳过补充', scene_id)
        return False

    # 3. 比对并更新
    return update_scene_metadata(stash_url, scene_id, scraped, current_info, stash_box_index)



def run_scans(stash_url, paths, do_scrape=True, stash_box_index=0):
    """
    完整流程：
      1. 简单扫描（路径入库）
      2. 等待完成
      3. 详细扫描（生成预览/指纹等）
      4. 等待完成
      5. 按路径查找场景 ID
      6. 对每个场景执行 Stash-box 刮削
      7. 等待刮削完成，执行元数据补充（自动识别 stash-box）
    """
    logger.info("🔄 扫描流水线启动 | 路径数=%d", len(paths))

    # ---- 1 & 2: 简单扫描 + 等待 ----
    logger.info("   ├─ [1/4] 简单扫描:")
    simple_job = scan_simple(stash_url, paths)
    if simple_job is None:
        logger.error('   └─ ❌ 简单扫描失败，流水线终止')
        return
    wait_for_job(stash_url, simple_job)

    # ---- 3 & 4: 详细扫描 + 等待 ----
    logger.info("   ├─ [2/4] 详细扫描:")
    detailed_job = scan_detailed(stash_url, paths)
    if detailed_job is None:
        logger.error('   └─ ❌ 详细扫描失败，流水线终止')
        return
    wait_for_job_running(stash_url, detailed_job)

    # ---- 5 & 6: 查场景 + 刮削 ----
    if not do_scrape:
        return

    logger.info("   ├─ [3/4] 查场景并刮削")
    scrape_jobs = []
    for p in paths:
        scene_ids = find_scenes_by_path(stash_url, p)
        if not scene_ids:
            logger.info("      └─ ⏭️ 未找到场景: %s", p)
            continue
        for sid in scene_ids:
            logger.info("      └─ 🔍 开始刮削场景 %s", sid)
            job_id = scrape_scene(stash_url, sid, stash_box_index)
            if job_id:
                scrape_jobs.append((job_id, sid))

    # ---- 7: 等待刮削完成 + 元数据补充（自动识别 stash-box）----
    if not scrape_jobs:
        logger.info('   └─ ⏭️ 无刮削任务，跳过补充')
        return

    logger.info("   └─ [4/4] 补充元数据:")
    for job_id, sid in scrape_jobs:
        status = wait_for_job(stash_url, job_id)
        if status is None or status.get("status") != "FINISHED":
            logger.warning("      └─ ⚠️ 场景 %s 刮削未完成（状态：%s），跳过",
                           sid, status.get('status') if status else '未知')
            continue

        stash_id = get_scene_stash_id(stash_url, sid)
        if not stash_id:
            logger.warning("      └─ ⚠️ 场景 %s 刮削完成但无 stash_id，跳过", sid)
            continue

        # 根据场景的 stash_ids 自动识别对应的 stash-box index
        auto_index = resolve_stash_box_index(stash_url, sid, stash_box_index)
        logger.info("      ├─ ✅ 刮削完成 | 场景 %s", sid)
        logger.info("      └─ 📝 补充元数据 | stash_id=%s | index=%d", stash_id, auto_index)
        enrich_scene_metadata(stash_url, sid, stash_id, auto_index)
