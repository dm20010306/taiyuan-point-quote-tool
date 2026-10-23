"""Knowledge-vault persistence for brands, projects, points and quotations.

SQLite remains the fast runtime index. Markdown snapshots in the active data
root are the authoritative business records and can rebuild that index.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path

import yaml
from backend.diagnostics import record_event
from backend.file_writes import atomic_write_text
from backend.path_resolver import get_paths


PATHS = get_paths(__file__)
APP_ROOT = PATHS.app_root
VAULT_ROOT = PATHS.knowledge_root
BRAND_DIR = VAULT_ROOT / "01_产品库" / "_品牌"
PROJECT_DIR = VAULT_ROOT / "06_客户档案" / "智能图纸与报价"
BACKUP_DIR = PROJECT_DIR / "_备份"
PROJECT_HISTORY_DIR = BACKUP_DIR / "项目历史"
CONFLICT_LOG = PROJECT_DIR / "同步冲突日志.md"
SCHEMA_VERSION = 2

PROJECT_TABLES = (
    ("projects", "id", "id"),
    ("drawings", "id", "project_id"),
    ("quotes", "id", "project_id"),
    ("points", "id", "project_id"),
    ("point_counters", "type_id", "project_id"),
)
QUOTE_TABLES = (
    ("extra_fees", "id"), ("quote_lines", "id"), ("manual_quote_lines", "id"),
    ("quotation_systems", "sort_order"), ("quotation_items", "sort_order"),
    ("quotation_versions", "version"),
)


def _atomic_write(path: Path, content: str) -> None:
    atomic_write_text(path, content)


def _digest(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_filename(value: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff-]+", "_", value).strip("_")[:60] or "记录"


def _parse_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8-sig")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if not match:
        return {}, text
    data = yaml.safe_load(match.group(1)) or {}
    return (data if isinstance(data, dict) else {}), text[match.end():]


def _table_columns(db: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in db.execute(f'PRAGMA table_info("{table}")')]


def _insert_rows(db: sqlite3.Connection, table: str, records: list[dict]) -> None:
    allowed = set(_table_columns(db, table))
    for record in records:
        values = {key: value for key, value in record.items() if key in allowed}
        columns = list(values)
        placeholders = ",".join("?" for _ in columns)
        db.execute(
            f'INSERT INTO "{table}" ({",".join(columns)}) VALUES ({placeholders})',
            [values[column] for column in columns],
        )


class KnowledgeRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._file_signatures: dict[tuple[str, str], tuple[int, int] | None] = {}
        for folder in (BRAND_DIR, PROJECT_DIR, BACKUP_DIR, PROJECT_HISTORY_DIR):
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except OSError:
                # Offline startup is supported when the local SQLite cache exists.
                pass

    def ensure_tables(self, db: sqlite3.Connection) -> None:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS knowledge_sync_state(
          entity_type TEXT NOT NULL,entity_id TEXT NOT NULL,cache_hash TEXT NOT NULL,
          vault_hash TEXT NOT NULL,synced_at TEXT NOT NULL,PRIMARY KEY(entity_type,entity_id));
        CREATE TABLE IF NOT EXISTS knowledge_sync_conflicts(
          id TEXT PRIMARY KEY,entity_type TEXT NOT NULL,entity_id TEXT NOT NULL,
          cache_hash TEXT NOT NULL,vault_hash TEXT NOT NULL,detected_at TEXT NOT NULL,
          resolved_at TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS knowledge_sync_runtime(
          id INTEGER PRIMARY KEY CHECK(id=1),status TEXT NOT NULL DEFAULT 'synced',
          last_attempt_at TEXT NOT NULL DEFAULT '',last_success_at TEXT NOT NULL DEFAULT '',
          failure_count INTEGER NOT NULL DEFAULT 0,last_error TEXT NOT NULL DEFAULT '',
          error_type TEXT NOT NULL DEFAULT '');
        """)
        db.execute("INSERT OR IGNORE INTO knowledge_sync_runtime(id) VALUES(1)")

    def record_sync_runtime(self, db: sqlite3.Connection, status: str, *, error: str = "", error_type: str = "", success: bool = False) -> None:
        attempted = datetime.now().astimezone().isoformat(timespec="seconds")
        db.execute(
            """UPDATE knowledge_sync_runtime SET status=?,last_attempt_at=?,
            last_success_at=CASE WHEN ? THEN ? ELSE last_success_at END,
            failure_count=failure_count+?,last_error=?,error_type=? WHERE id=1""",
            (status, attempted, int(success), attempted, int(bool(error)), error[:1000], error_type),
        )

    def pending_entities(self, db: sqlite3.Connection) -> list[dict]:
        """Rebuild pending state from the local cache versus its last synced hash."""
        pending = []
        for entity_id in (row[0] for row in db.execute("SELECT id FROM brands")):
            cache = self.brand_from_db(db, entity_id)
            state = self._state(db, "brand", entity_id)
            if cache and (not state or _digest(cache) != state["cache_hash"]):
                pending.append({"entity_type": "brand", "entity_id": entity_id})
        for entity_id in (row[0] for row in db.execute("SELECT id FROM projects")):
            cache = self.snapshot_project(db, entity_id)
            state = self._state(db, "project", entity_id)
            if cache and (not state or _digest(cache) != state["cache_hash"]):
                pending.append({"entity_type": "project", "entity_id": entity_id})
        return pending

    def backup_before_first_migration(self, db: sqlite3.Connection) -> Path | None:
        marker = BACKUP_DIR / "migration-v1.done"
        if marker.exists() or not self.db_path.is_file():
            return None
        has_business_data = any(db.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone() for table in ("brands", "projects"))
        if not has_business_data:
            _atomic_write(marker, datetime.now().isoformat())
            return None
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = BACKUP_DIR / f"app-before-knowledge-sync-{stamp}.sqlite3"
        shutil.copy2(self.db_path, target)
        _atomic_write(marker, f"{datetime.now().isoformat()}\n{target.name}\n")
        return target

    def brand_path(self, brand_id: str) -> Path:
        return BRAND_DIR / f"{brand_id}.md"

    def brand_from_db(self, db: sqlite3.Connection, brand_id: str) -> dict | None:
        row = db.execute("SELECT * FROM brands WHERE id=?", (brand_id,)).fetchone()
        if not row:
            return None
        value = dict(row)
        try:
            value["aliases"] = json.loads(value.get("aliases") or "[]")
        except json.JSONDecodeError:
            value["aliases"] = []
        return value

    def read_brand(self, path: Path) -> dict | None:
        try:
            data, _ = _parse_frontmatter(path)
        except (OSError, UnicodeError, yaml.YAMLError):
            return None
        if data.get("类型") != "报价品牌" or not re.fullmatch(r"[a-f0-9]{32}", str(data.get("id") or "")):
            return None
        return {
            "id": str(data["id"]), "name": str(data.get("名称") or ""),
            "english_name": str(data.get("英文名") or ""),
            "aliases": list(data.get("别名") or []), "enabled": int(bool(data.get("启用", True))),
            "note": str(data.get("备注") or ""), "logo_svg_path": data.get("SVG_Logo") or None,
            "logo_png_path": data.get("PNG_Logo") or None,
            "created_at": str(data.get("创建时间") or data.get("更新时间") or ""),
            "updated_at": str(data.get("更新时间") or ""),
        }

    def write_brand(self, brand: dict) -> str:
        normalized = {**brand, "aliases": list(brand.get("aliases") or [])}
        meta = {
            "id": normalized["id"], "类型": "报价品牌", "名称": normalized["name"],
            "英文名": normalized.get("english_name", ""), "别名": normalized["aliases"],
            "SVG_Logo": normalized.get("logo_svg_path") or "", "PNG_Logo": normalized.get("logo_png_path") or "",
            "启用": bool(normalized.get("enabled", 1)), "备注": normalized.get("note", ""),
            "创建时间": normalized.get("created_at", ""), "更新时间": normalized.get("updated_at", ""),
        }
        aliases = "、".join(normalized["aliases"]) or "—"
        body = f"# {normalized['name']}\n\n| 项 | 值 |\n| --- | --- |\n| 英文名 | {normalized.get('english_name','')} |\n| 别名 | {aliases} |\n| 状态 | {'启用' if normalized.get('enabled',1) else '停用'} |\n\n{normalized.get('note','')}\n"
        content = "---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=1000) + "---\n" + body
        _atomic_write(self.brand_path(normalized["id"]), content)
        return _digest(normalized)

    def project_path(self, project_id: str) -> Path | None:
        for path in PROJECT_DIR.glob("*.md"):
            try:
                data, _ = _parse_frontmatter(path)
                if str(data.get("id")) == project_id and data.get("类型") == "智能图纸报价项目":
                    return path
            except Exception:
                continue
        return None

    def snapshot_project(self, db: sqlite3.Connection, project_id: str) -> dict | None:
        project = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if not project:
            return None
        snapshot = {"schema_version": SCHEMA_VERSION, "tables": {}}
        quote = db.execute("SELECT id FROM quotes WHERE project_id=?", (project_id,)).fetchone()
        for table, order, foreign_key in PROJECT_TABLES:
            records = [dict(row) for row in db.execute(f'SELECT * FROM "{table}" WHERE {foreign_key}=? ORDER BY "{order}"', (project_id,))]
            snapshot["tables"][table] = records
        snapshot["tables"]["floors"] = [dict(row) for row in db.execute("SELECT * FROM floors WHERE project_id=? ORDER BY sort_order,id",(project_id,))]
        # Keep the user-managed project folder list recoverable with project notes.
        snapshot["tables"]["project_folders"] = [dict(row) for row in db.execute("SELECT * FROM project_folders ORDER BY sort_order,name")]
        snapshot["tables"]["layers"] = [dict(row) for row in db.execute("SELECT l.* FROM layers l JOIN floors f ON f.id=l.floor_id WHERE f.project_id=? ORDER BY l.sort_order,l.id",(project_id,))]
        quote_id = quote[0] if quote else None
        for table, order in QUOTE_TABLES:
            records = [dict(row) for row in db.execute(f'SELECT * FROM "{table}" WHERE quote_id=? ORDER BY "{order}"', (quote_id,))] if quote_id else []
            snapshot["tables"][table] = records
        return snapshot

    def read_project(self, path: Path) -> dict | None:
        try:
            meta, body = _parse_frontmatter(path)
            match = re.search(r"<!-- pointquote-data:start -->\s*```json\s*(.*?)\s*```\s*<!-- pointquote-data:end -->", body, re.S)
            snapshot = json.loads(match.group(1)) if match else None
        except (OSError, UnicodeError, yaml.YAMLError, json.JSONDecodeError):
            return None
        if meta.get("类型") != "智能图纸报价项目" or not isinstance(snapshot, dict):
            return None
        projects = snapshot.get("tables", {}).get("projects", [])
        if len(projects) == 1:
            project = projects[0]
            project["name"] = str(meta.get("项目名称") or project.get("name") or "")
            project["customer"] = str(meta.get("客户") or "")
            project["address"] = str(meta.get("地址") or "")
            project["status"] = str(meta.get("状态") or project.get("status") or "进行中")
            project["signed"] = int(bool(meta.get("已签", project.get("signed", 0))))
            project["updated_at"] = str(meta.get("更新时间") or project.get("updated_at") or "")
        return snapshot

    def write_project(self, snapshot: dict) -> tuple[Path, str]:
        project = snapshot["tables"]["projects"][0]
        existing = self.project_path(project["id"])
        path = existing or PROJECT_DIR / f"{_safe_filename(project['name'])}-{project['id'][:8]}.md"
        meta = {
            "id": project["id"], "类型": "智能图纸报价项目", "项目名称": project["name"],
            "客户": project.get("customer", ""), "地址": project.get("address", ""),
            "状态": project.get("status", ""), "已签": bool(project.get("signed", 0)),
            "创建时间": project.get("created_at", ""), "更新时间": project.get("updated_at", ""),
            "数据结构版本": SCHEMA_VERSION,
        }
        payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2)
        body = f"# {project['name']}\n\n> 本文件由智能图纸点位与报价工具维护。可读信息位于上方，完整可恢复数据位于下方。\n\n<!-- pointquote-data:start -->\n```json\n{payload}\n```\n<!-- pointquote-data:end -->\n"
        content = "---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=1000) + "---\n" + body
        if path.exists():
            previous = path.read_text(encoding="utf-8")
            if previous != content:
                history = PROJECT_HISTORY_DIR / project["id"]
                history.mkdir(parents=True, exist_ok=True)
                saved = history / f"{datetime.now():%Y%m%d-%H%M%S-%f}.md"
                _atomic_write(saved, previous)
                versions = sorted(history.glob("*.md"), key=lambda item:item.name, reverse=True)
                for obsolete in versions[30:]:
                    obsolete.unlink()
        _atomic_write(path, content)
        return path, _digest(snapshot)

    def restore_project(self, db: sqlite3.Connection, snapshot: dict) -> None:
        project_rows = snapshot.get("tables", {}).get("projects", [])
        if len(project_rows) != 1:
            raise ValueError("项目知识库文件缺少唯一项目记录")
        project_id = project_rows[0]["id"]
        db.execute("DELETE FROM projects WHERE id=?", (project_id,))
        tables=snapshot["tables"]
        for folder in tables.get("project_folders", []):
            columns = list(folder)
            db.execute(
                f"INSERT OR IGNORE INTO project_folders({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",
                [folder[column] for column in columns],
            )
        floors=tables.get("floors") or []
        layers=tables.get("layers") or []
        if not floors:
            floor_id=uuid.uuid5(uuid.NAMESPACE_URL,project_id+"/default-floor").hex
            floors=[{"id":floor_id,"project_id":project_id,"name":"默认楼层","sort_order":0}]
        if not layers:
            layer_id=uuid.uuid5(uuid.NAMESPACE_URL,project_id+"/default-layer").hex
            layers=[{"id":layer_id,"floor_id":floors[0]["id"],"name":"默认图层","sort_order":0,"visible":1,"locked":0}]
        for table in ("projects", "drawings", "quotes", "points", "point_counters"):
            records = snapshot["tables"].get(table, [])
            if table == "drawings":
                records=[{**record,"floor_id":record.get("floor_id") or floors[0]["id"]} for record in records]
            if table == "points":
                known_products = {row[0] for row in db.execute("SELECT id FROM products")}
                records = [{**record, "layer_id": record.get("layer_id") or layers[0]["id"], "product_id": record.get("product_id") if record.get("product_id") in known_products else None} for record in records]
            if table == "drawings":
                _insert_rows(db,"floors",floors)
                _insert_rows(db,"layers",layers)
            _insert_rows(db, table, records)
        for table, _ in QUOTE_TABLES:
            _insert_rows(db, table, snapshot["tables"].get(table, []))

    def restore_local_records(self, db: sqlite3.Connection) -> dict:
        """Rebuild business index rows from local Markdown without sync/conflict logic."""
        self.ensure_tables(db)
        brand_count = 0
        db.execute("DELETE FROM projects")
        db.execute("DELETE FROM products")
        db.execute("DELETE FROM brands")
        brands = [brand for path in BRAND_DIR.glob("*.md") if (brand := self.read_brand(path))]
        for brand in brands:
            db.execute("""INSERT INTO brands(id,name,english_name,aliases,logo_svg_path,logo_png_path,enabled,note,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,english_name=excluded.english_name,aliases=excluded.aliases,
                logo_svg_path=excluded.logo_svg_path,logo_png_path=excluded.logo_png_path,
                enabled=excluded.enabled,note=excluded.note,updated_at=excluded.updated_at""",
                (brand["id"], brand["name"], brand["english_name"], json.dumps(brand["aliases"], ensure_ascii=False),
                 brand["logo_svg_path"], brand["logo_png_path"], brand["enabled"], brand["note"], brand["created_at"], brand["updated_at"]))
            brand_count += 1
        return {"brands": brand_count}

    def restore_local_projects(self, db: sqlite3.Connection) -> int:
        """Restore project snapshots after local product IDs have been indexed."""
        snapshots = [snapshot for path in PROJECT_DIR.glob("*.md") if (snapshot := self.read_project(path))]
        for snapshot in snapshots:
            self.restore_project(db, snapshot)
        return len(snapshots)

    def _state(self, db, kind: str, entity_id: str):
        row = db.execute("SELECT * FROM knowledge_sync_state WHERE entity_type=? AND entity_id=?", (kind, entity_id)).fetchone()
        return dict(row) if row else None

    def _save_state(self, db, kind: str, entity_id: str, cache_hash: str, vault_hash: str) -> None:
        db.execute("""INSERT INTO knowledge_sync_state VALUES(?,?,?,?,?)
          ON CONFLICT(entity_type,entity_id) DO UPDATE SET cache_hash=excluded.cache_hash,vault_hash=excluded.vault_hash,synced_at=excluded.synced_at""",
          (kind, entity_id, cache_hash, vault_hash, datetime.now().isoformat()))

    def _conflict(self, db, kind: str, entity_id: str, cache_hash: str, vault_hash: str) -> dict:
        key = _digest([kind, entity_id, cache_hash, vault_hash])[:32]
        detected = datetime.now().isoformat()
        db.execute("INSERT OR IGNORE INTO knowledge_sync_conflicts VALUES(?,?,?,?,?,?,?)", (key, kind, entity_id, cache_hash, vault_hash, detected, ""))
        if not CONFLICT_LOG.exists() or key not in CONFLICT_LOG.read_text(encoding="utf-8"):
            previous = CONFLICT_LOG.read_text(encoding="utf-8") if CONFLICT_LOG.exists() else "# 知识库同步冲突日志\n\n"
            _atomic_write(CONFLICT_LOG, previous + f"## {detected}｜{kind}:{entity_id}\n\n- 冲突ID：`{key}`\n- 缓存摘要：`{cache_hash}`\n- 知识库摘要：`{vault_hash}`\n- 处理状态：待人工确认，系统未静默覆盖。\n\n")
        return {"id": key, "entity_type": kind, "entity_id": entity_id}

    def sync(self, db: sqlite3.Connection) -> dict:
        started = time.perf_counter()
        scan_ms = parse_ms = read_ms = write_ms = 0.0
        reads = writes = 0
        if not BRAND_DIR.is_dir() or not PROJECT_DIR.is_dir():
            raise FileNotFoundError("知识库目录当前不可访问")
        self.ensure_tables(db)
        conflicts = []
        unchanged_entities_skipped = 0
        # Brands: notes are authoritative once present; absent notes are migrated from SQLite.
        brand_ids = {row[0] for row in db.execute("SELECT id FROM brands")}
        phase = time.perf_counter()
        brand_paths = list(BRAND_DIR.glob("*.md"))
        scan_ms += (time.perf_counter() - phase) * 1000
        brand_ids.update(path.stem for path in brand_paths if re.fullmatch(r"[a-f0-9]{32}", path.stem))
        for entity_id in sorted(brand_ids):
            cache = self.brand_from_db(db, entity_id)
            path = self.brand_path(entity_id)
            state = self._state(db, "brand", entity_id)
            cache_hash = _digest(cache) if cache else ""
            phase = time.perf_counter()
            try:
                stat_result = path.stat()
                signature = (stat_result.st_mtime_ns, stat_result.st_size)
            except OSError:
                signature = None
            scan_ms += (time.perf_counter() - phase) * 1000
            signature_key = ("brand", entity_id)
            if (state and signature is not None
                    and self._file_signatures.get(signature_key) == signature
                    and cache_hash == state["cache_hash"]):
                unchanged_entities_skipped += 1
                continue
            if signature is not None:
                phase = time.perf_counter(); vault = self.read_brand(path); read_ms += (time.perf_counter() - phase) * 1000; reads += 1
            else:
                vault = None
            vault_hash = _digest(vault) if vault else ""
            if not state:
                if vault:
                    db.execute("INSERT OR REPLACE INTO brands(id,name,english_name,aliases,logo_svg_path,logo_png_path,enabled,note,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                               (vault["id"],vault["name"],vault["english_name"],json.dumps(vault["aliases"],ensure_ascii=False),vault["logo_svg_path"],vault["logo_png_path"],vault["enabled"],vault["note"],vault["created_at"],vault["updated_at"]))
                    cache_hash = vault_hash
                elif cache:
                    phase = time.perf_counter(); vault_hash = self.write_brand(cache); write_ms += (time.perf_counter() - phase) * 1000; writes += 1
                if cache or vault:
                    self._save_state(db, "brand", entity_id, cache_hash, vault_hash)
                self._file_signatures[signature_key] = signature
                continue
            cache_changed, vault_changed = cache_hash != state["cache_hash"], vault_hash != state["vault_hash"]
            if cache_changed and vault_changed and cache_hash != vault_hash:
                conflicts.append(self._conflict(db, "brand", entity_id, cache_hash, vault_hash)); continue
            if vault_changed and vault:
                db.execute("UPDATE brands SET name=?,english_name=?,aliases=?,logo_svg_path=?,logo_png_path=?,enabled=?,note=?,created_at=?,updated_at=? WHERE id=?",
                           (vault["name"],vault["english_name"],json.dumps(vault["aliases"],ensure_ascii=False),vault["logo_svg_path"],vault["logo_png_path"],vault["enabled"],vault["note"],vault["created_at"],vault["updated_at"],entity_id))
                cache_hash = vault_hash
            elif cache_changed and cache:
                phase = time.perf_counter(); vault_hash = self.write_brand(cache); write_ms += (time.perf_counter() - phase) * 1000; writes += 1
            elif not vault:
                conflicts.append(self._conflict(db, "brand", entity_id, cache_hash, vault_hash)); continue
            self._save_state(db, "brand", entity_id, cache_hash, vault_hash)
            self._file_signatures[signature_key] = signature

        project_paths = {}
        phase = time.perf_counter(); project_note_paths = list(PROJECT_DIR.glob("*.md")); scan_ms += (time.perf_counter() - phase) * 1000
        phase = time.perf_counter()
        for path in project_note_paths:
            try:
                meta, _ = _parse_frontmatter(path)
                if meta.get("类型") == "智能图纸报价项目": project_paths[str(meta.get("id"))] = path
            except Exception:
                continue
        parse_ms += (time.perf_counter() - phase) * 1000
        project_ids = {row[0] for row in db.execute("SELECT id FROM projects")} | set(project_paths)
        for entity_id in sorted(project_ids):
            cache = self.snapshot_project(db, entity_id)
            path = project_paths.get(entity_id)
            state = self._state(db, "project", entity_id)
            cache_hash = _digest(cache) if cache else ""
            phase = time.perf_counter()
            try:
                stat_result = path.stat() if path else None
                signature = (stat_result.st_mtime_ns, stat_result.st_size) if stat_result else None
            except OSError:
                signature = None
            scan_ms += (time.perf_counter() - phase) * 1000
            signature_key = ("project", entity_id)
            if (state and signature is not None
                    and self._file_signatures.get(signature_key) == signature
                    and cache_hash == state["cache_hash"]):
                unchanged_entities_skipped += 1
                continue
            if signature is not None:
                phase = time.perf_counter(); vault = self.read_project(path); read_ms += (time.perf_counter() - phase) * 1000; reads += 1
            else:
                vault = None
            vault_hash = _digest(vault) if vault else ""
            if not state:
                if vault:
                    self.restore_project(db, vault); cache_hash = vault_hash
                elif cache:
                    phase = time.perf_counter(); _, vault_hash = self.write_project(cache); write_ms += (time.perf_counter() - phase) * 1000; writes += 1
                if cache or vault:
                    self._save_state(db, "project", entity_id, cache_hash, vault_hash)
                self._file_signatures[signature_key] = signature
                continue
            cache_changed, vault_changed = cache_hash != state["cache_hash"], vault_hash != state["vault_hash"]
            if cache_changed and vault_changed and cache_hash != vault_hash:
                conflicts.append(self._conflict(db, "project", entity_id, cache_hash, vault_hash)); continue
            if vault_changed and vault:
                self.restore_project(db, vault); cache_hash = vault_hash
            elif cache_changed and cache:
                phase = time.perf_counter(); _, vault_hash = self.write_project(cache); write_ms += (time.perf_counter() - phase) * 1000; writes += 1
            elif not vault and cache:
                conflicts.append(self._conflict(db, "project", entity_id, cache_hash, vault_hash)); continue
            elif not cache and vault:
                self.restore_project(db, vault); cache_hash = vault_hash
            self._save_state(db, "project", entity_id, cache_hash, vault_hash)
            self._file_signatures[signature_key] = signature
        metrics = {
            "brand_files_scanned": len(brand_paths),
            "project_files_scanned": len(project_note_paths),
            "unchanged_entities_skipped": unchanged_entities_skipped,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "scan_ms": round(scan_ms, 2), "parse_ms": round(parse_ms, 2),
            "read_ms": round(read_ms, 2), "write_ms": round(write_ms, 2),
            "files_read": reads, "files_written": writes,
        }
        record_event("knowledgeBase.scan", operation="inventory", durationMs=metrics["scan_ms"], success=True, projectFiles=len(project_note_paths), brandFiles=len(brand_paths))
        record_event("knowledgeBase.parse", operation="frontmatter", durationMs=metrics["parse_ms"], success=True, projectFiles=len(project_note_paths))
        record_event("knowledgeBase.read", operation="read", durationMs=metrics["read_ms"], success=True, fileCount=reads)
        record_event("knowledgeBase.write", operation="write", durationMs=metrics["write_ms"], success=True, fileCount=writes)
        record_event("vault_sync", operation="scan", durationMs=metrics["duration_ms"], success=True, **metrics)
        return {"conflicts": conflicts, "brands": len(brand_ids), "projects": len(project_ids), "metrics": metrics}

    def delete_project_note(self, db: sqlite3.Connection, project_id: str) -> None:
        path = self.project_path(project_id)
        if path and path.exists():
            path.unlink()
        db.execute("DELETE FROM knowledge_sync_state WHERE entity_type='project' AND entity_id=?", (project_id,))

    def status(self, db: sqlite3.Connection) -> dict:
        return {
            "vault_root": str(VAULT_ROOT), "brand_dir": str(BRAND_DIR), "project_dir": str(PROJECT_DIR),
            "brand_notes": len(list(BRAND_DIR.glob("*.md"))),
            "project_notes": sum(1 for path in PROJECT_DIR.glob("*.md") if self.read_project(path)),
            "conflicts": [dict(row) for row in db.execute("SELECT * FROM knowledge_sync_conflicts WHERE resolved_at='' ORDER BY detected_at DESC")],
        }
