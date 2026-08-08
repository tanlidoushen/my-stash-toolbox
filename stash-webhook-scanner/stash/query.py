"""所有 GraphQL 查询/变更字符串集中管理。"""

# ── 扫描 ─────────────────────────────────────────────────────

METADATA_SCAN = """
mutation MetadataScan($input: ScanMetadataInput!) {
  metadataScan(input: $input)
}
"""

FIND_JOB = """
query FindJob($input: FindJobInput!) {
  findJob(input: $input) { id status progress description startTime endTime error }
}
"""

JOB_QUEUE = """
query GetJobQueue {
  jobQueue { id status subTasks description progress startTime endTime addTime error }
}
"""

# ── 场景 ─────────────────────────────────────────────────────

FIND_SCENES_BY_PATH = """
query FindSceneByPath($filter: SceneFilterType!) {
  findScenes(scene_filter: $filter) { count scenes { id files { path size } } }
}
"""

FIND_SCENE = """
query FindScene($id: ID!) {
  findScene(id: $id) { id title code stash_ids { endpoint stash_id } studio { id name } performers { id name stash_ids { endpoint stash_id } } tags { id name } }
}
"""

FIND_SCENE_STASH_IDS = """
query FindScene($id: ID!) {
  findScene(id: $id) { id stash_ids { endpoint stash_id } }
}
"""

SCENE_UPDATE = """
mutation UpdateScene($input: SceneUpdateInput!) {
  sceneUpdate(input: $input) { id title code date studio { id name } performers { id name } tags { id name } }
}
"""

# ── 标签 ─────────────────────────────────────────────────────

FIND_TAGS = """
query FindTags($filter: FindFilterType) {
  findTags(filter: $filter) { tags { id name aliases } }
}
"""

TAG_CREATE = """
mutation CreateTag($input: TagCreateInput!) {
  tagCreate(input: $input) { id name }
}
"""

# ── 演员 ─────────────────────────────────────────────────────

FIND_PERFORMERS = """
query FindPerformers($filter: FindFilterType) {
  findPerformers(filter: $filter) { count performers { id name alias_list } }
}
"""

PERFORMER_CREATE = """
mutation CreatePerformer($input: PerformerCreateInput!) {
  performerCreate(input: $input) {
    id name image_path
    stash_ids { endpoint stash_id }
  }
}
"""

PERFORMER_QUERY_FOR_STASH_BOX = """
query ScrapeSingleScene($source: ScraperSourceInput!, $input: ScrapeSingleSceneInput!) {
  scrapeSingleScene(source: $source, input: $input) { performers { stored_id images name gender urls birthdate country height measurements aliases remote_site_id disambiguation ethnicity eye_color hair_color fake_tits career_start career_end tattoos } }
}
"""

# ── 工作室 ───────────────────────────────────────────────────

FIND_STUDIOS = """
query FindStudios($filter: FindFilterType, $studio_filter: StudioFilterType) {
  findStudios(filter: $filter, studio_filter: $studio_filter) { count studios { id name } }
}
"""

STUDIO_CREATE = """
mutation CreateStudio($input: StudioCreateInput!) {
  studioCreate(input: $input) { id name }
}
"""

# ── stash-box 刮削 ─────────────────────────────────────────

SCRAPE_SINGLE_SCENE = """
query ScrapeSingleScene($source: ScraperSourceInput!, $input: ScrapeSingleSceneInput!) {
  scrapeSingleScene(source: $source, input: $input) {
    title code details director urls date image remote_site_id
    studio { stored_id name url parent { stored_id name url parent { stored_id name url } } image remote_site_id }
    tags { name }
    performers { stored_id images name gender urls birthdate country height measurements aliases remote_site_id disambiguation ethnicity eye_color hair_color fake_tits career_start career_end tattoos }
  }
}
"""

METADATA_IDENTIFY = """
mutation StartFallbackIdentify {
  metadataIdentify(input: { sources: [{ source: { stash_box_index: IDX } options: { includeMalePerformers: true setCoverImage: true setOrganized: true skipMultipleMatches: false fieldOptions: [ { field: "TITLE", strategy: OVERWRITE } { field: "STUDIO", strategy: MERGE, createMissing: true } { field: "DATE", strategy: MERGE } { field: "DETAILS", strategy: MERGE } { field: "URLS", strategy: MERGE } { field: "PERFORMERS", strategy: MERGE, createMissing: true } { field: "TAGS", strategy: MERGE, createMissing: true } { field: "STUDIO_CODE", strategy: MERGE } { field: "DIRECTOR", strategy: MERGE } { field: "STASH_IDS", strategy: MERGE } ] } } ] sceneIDs: ["SID"] })
}
"""

# ── 通知 ─────────────────────────────────────────────────────

SCENE_FOR_NOTIFICATION = """
query GetSceneDetails($id: ID!) {
  findScene(id: $id) {
    id title details date director code
    files { path size duration }
    paths { screenshot }
    tags { id name }
    performers { id name gender }
    studio { id name }
  }
}
"""

# ── 删除场景 ─────────────────────────────────────────────────

SCENE_DESTROY = """
mutation DestroyScene($id: ID!) {
  sceneDestroy(input: { id: $id })
}
"""

# ── 按番号查询场景 ─────────────────────────────────────────

FIND_SCENES_BY_CODE = """
query FindScenesByCode($filter: SceneFilterType!) {
  findScenes(scene_filter: $filter) {
    count
    scenes { id title code date studio { id name } performers { id name gender } files { path size } }
  }
}
"""

# ── 从 URL 刮削场景 ─────────────────────────────────

SCRAPE_SCENE_URL = """
query ScrapeSceneURL($url: String!) {
  scrapeSceneURL(url: $url) {
    urls
    title
    date
    studio {
      stored_id
      url
      image
      details
      aliases
      remote_site_id
    }
    image
    director
    details
    tags {
      name
      stored_id
    }
    performers {
      stored_id
      name
      images
      aliases
      disambiguation
      gender
      url
      twitter
      instagram
      birthdate
      ethnicity
      country
      eye_color
      height
      measurements
      fake_tits
      penis_length
      circumcised
      career_length
      career_start
      career_end
      tattoos
      piercings
      aliases
      image
      details
      death_date
      hair_color
      weight
      remote_site_id
    }
    code
  }
}
"""

# ── 服务器统计 ─────────────────────────────────────────────

LIBRARY_STATS = """
query LibraryStats {
  findScenes(filter: { per_page: 0 }) { count }
  findPerformers(filter: { per_page: 0 }) { count }
  findStudios(filter: { per_page: 0 }) { count }
  findTags(filter: { per_page: 0 }) { count }
}
"""