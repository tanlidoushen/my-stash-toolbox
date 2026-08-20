"""SQLite 校验码库：建表/索引/upsert/查询（/app/data/checksums.db）。"""

import json
import logging
import os
import sqlite3
import threading
import time

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_FILE = os.path.join(_DATA_DIR, "checksums.db")
_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS file_checksums (
  cd2_path       TEXT PRIMARY KEY,
  stash_scene_id TEXT,
  file_size      INTEGER,
  ed2k           TEXT,
  sha1           TEXT,
  md5            TEXT,
  oshash         TEXT,
  phash          TEXT,
  code           TEXT,
  title          TEXT,
  region         TEXT,
  stash_ids      TEXT,
  source         TEXT,
  calculated_at  TEXT,
  updated_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_file_checksums_scene ON file_checksums(stash_scene_id);
CREATE INDEX IF NOT EXISTS idx_file_checksums_ed2k  ON file_checksums(ed2k);
CREATE INDEX IF NOT EXISTS idx_file_checksums_sha1  ON file_checksums(sha1);
"""

_EXTRA_COLUMNS = {
    "title": "TEXT",
    "region": "TEXT",
}


def _connect():
    os.makedirs(_DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """建表/索引 + 老库补列迁移（幂等）。启动时调用一次即可。"""
    with _lock:
        conn = _connect()
        try:
            conn.executescript(_SCHEMA)
            cols = {r[1] for r in conn.execute("PRAGMA table_info(file_checksums)")}
            for name, typ in _EXTRA_COLUMNS.items():
                if name not in cols:
                    conn.execute("ALTER TABLE file_checksums ADD COLUMN %s %s" % (name, typ))
                    logger.info("校验码库迁移: 加列 %s %s", name, typ)
            conn.commit()
        finally:
            conn.close()


def upsert_checksums(cd2_path, stash_scene_id, file_size, checksums, source="run_scans"):
    """写入/更新一行。

    checksums: dict，可选键 ed2k/sha1/md5/oshash/phash/code/title/region/stash_ids。
    幂等：ed2k 只在已有值缺失时填（算过一次不重算）；直取码每次刷新。
    """
    stash_ids = checksums.get("stash_ids")
    if isinstance(stash_ids, (list, dict)):
        stash_ids = json.dumps(stash_ids, ensure_ascii=False)
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO file_checksums
                  (cd2_path, stash_scene_id, file_size, ed2k, sha1, md5, oshash, phash,
                   code, title, region, stash_ids, source, calculated_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(cd2_path) DO UPDATE SET
                  stash_scene_id=excluded.stash_scene_id,
                  file_size=excluded.file_size,
                  ed2k=COALESCE(excluded.ed2k, file_checksums.ed2k),
                  sha1=excluded.sha1,
                  md5=excluded.md5,
                  oshash=excluded.oshash,
                  phash=excluded.phash,
                  code=excluded.code,
                  title=excluded.title,
                  region=excluded.region,
                  stash_ids=excluded.stash_ids,
                  source=excluded.source,
                  updated_at=excluded.updated_at
                """,
                (cd2_path, str(stash_scene_id), file_size,
                 checksums.get("ed2k"), checksums.get("sha1"), checksums.get("md5"),
                 checksums.get("oshash"), checksums.get("phash"),
                 checksums.get("code"), checksums.get("title"), checksums.get("region"),
                 stash_ids, source, now, now),
            )
            conn.commit()
        finally:
            conn.close()


def _row_to_dict(row):
    d = dict(row)
    if d.get("stash_ids"):
        try:
            d["stash_ids"] = json.loads(d["stash_ids"])
        except (json.JSONDecodeError, TypeError):
            pass
    return d


def get_by_cd2_path(cd2_path):
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM file_checksums WHERE cd2_path = ?", (cd2_path,)
            ).fetchone()
            return _row_to_dict(row) if row else None
        finally:
            conn.close()


def get_by_scene_id(scene_id):
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM file_checksums WHERE stash_scene_id = ?",
                (str(scene_id),),
            ).fetchone()
            return _row_to_dict(row) if row else None
        finally:
            conn.close()


def get_by_hash(hash_type, value):
    """按校验码查（ed2k/sha1/md5/oshash/phash），返回首条或 None。"""
    allowed = ("ed2k", "sha1", "md5", "oshash", "phash")
    if hash_type not in allowed:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM file_checksums WHERE %s = ?" % hash_type,
                (value,),
            ).fetchone()
            return _row_to_dict(row) if row else None
        finally:
            conn.close()
