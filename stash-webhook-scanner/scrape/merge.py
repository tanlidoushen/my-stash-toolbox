"""Plugin 数据合并工具。"""

import logging

logger = logging.getLogger(__name__)


def merge_plugin_into_scraped(scraped_data, extra_data):
    """Merge plugin-scraped data into scraped_data before scene update.

    Supported extra_data keys:
      - title        (overrides scraped title)
      - details      (overrides scraped details)
      - performers   (appends unique performers by name)
      - tags         (appends unique tags by name)
      - urls         (appends unique URLs)
    """
    changes = []

    # title
    plugin_title = extra_data.get("title")
    if plugin_title:
        scraped_data["title"] = plugin_title
        changes.append("标题")

    # details
    plugin_details = extra_data.get("details")
    if plugin_details:
        scraped_data["details"] = plugin_details
        changes.append("简介")

    # performers
    plugin_performers = extra_data.get("performers", [])
    if plugin_performers:
        existing = scraped_data.get("performers", [])
        existing_names = {p.get("name") for p in existing if p.get("name")}
        added = []
        for p in plugin_performers:
            name = p.get("name")
            if name and name not in existing_names:
                entry = {"name": name}
                if p.get("gender"):
                    entry["gender"] = p["gender"]
                if p.get("urls"):
                    entry["urls"] = p["urls"]
                existing.append(entry)
                existing_names.add(name)
                added.append(name)
        scraped_data["performers"] = existing
        if added:
            changes.append("演员=%s" % ",".join(added))

    # tags
    plugin_tags = extra_data.get("tags", [])
    if plugin_tags:
        existing_tags = scraped_data.get("tags", [])
        existing_tag_names = {t.get("name") for t in existing_tags if t.get("name")}
        added_tags = []
        for t in plugin_tags:
            name = t.get("name")
            if name and name not in existing_tag_names:
                existing_tags.append(t)
                existing_tag_names.add(name)
                added_tags.append(name)
        scraped_data["tags"] = existing_tags
        if added_tags:
            changes.append("标签=%d个" % len(added_tags))

    # urls
    plugin_urls = extra_data.get("urls", [])
    if plugin_urls:
        existing_urls = scraped_data.get("urls", []) or []
        existing_set = set(existing_urls)
        new_count = 0
        for u in plugin_urls:
            if u not in existing_set:
                existing_urls.append(u)
                existing_set.add(u)
                new_count += 1
        scraped_data["urls"] = existing_urls
        if new_count:
            changes.append("URL=%d条" % new_count)

    if changes:
        logger.info("         - [Plugin] 合并: %s", " | ".join(changes))

