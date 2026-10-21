"""Obsidian Markdown notes are the authoritative product catalog."""
from __future__ import annotations

import os
import re
import stat
import time
import uuid
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml
from backend.diagnostics import record_event
from backend.file_writes import atomic_write_text
from backend.path_resolver import get_paths
from backend.quotation_v2 import SYSTEM_BY_ID, canonical_system_category

PATHS = get_paths(__file__)
APP_ROOT = PATHS.app_root
VAULT_ROOT = PATHS.knowledge_root
PRODUCT_DIR = VAULT_ROOT / "01_产品库"
IMAGE_DIR = VAULT_ROOT / "09_附件" / "产品图片"
BRAND_LOGO_DIR = VAULT_ROOT / "09_附件" / "品牌Logo"
for _vault_folder in (PRODUCT_DIR, IMAGE_DIR, BRAND_LOGO_DIR):
    try:
        _vault_folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        # The local runtime can start from its SQLite cache while a network vault
        # is unavailable; writes still fail visibly until the share returns.
        pass

PRODUCT_CATEGORIES = ("智能", "影音", "灯光", "网络")
# Preserve existing product-library directories even when quote-facing labels change.
SYSTEM_FOLDER_BY_ID = {key: value["name_zh"] for key, value in SYSTEM_BY_ID.items()}
SYSTEM_FOLDER_BY_ID.update({
    "curtain": "电动窗帘系统",
    "hvac": "暖通管理系统",
    "music": "背景音乐系统",
    "lighting-control": "灯控系统",
})
DEVICE_TYPE_NAMES = {
    "switch":"智能开关", "curtain":"窗帘", "sensor":"人体传感器", "water":"水浸传感器",
    "thermostat":"温控器", "light":"调光", "lock":"智能门禁", "camera":"摄像头",
    "ceiling_ap":"吸顶 AP", "wall_ap":"墙面 AP", "network":"网络设备（历史兼容）",
    "av":"影音设备", "system":"智能系统", "other":"其他设备",
    "cloud_gateway":"云网关主机", "network_switch":"交换机", "poe_switch":"POE交换机", "cable":"线材",
}
LEGACY_TYPE_BY_CATEGORY = {
    "智能开关":"switch", "窗帘":"curtain", "人体传感器":"sensor", "水浸传感器":"water",
    "温控器":"thermostat", "调光":"light", "灯光":"light", "灯带":"light", "灯光控制模块":"light",
    "智能门禁":"lock", "门锁":"lock", "摄像头":"camera", "吸顶 AP":"ceiling_ap",
    "吸顶AP":"ceiling_ap", "墙面 AP":"wall_ap", "墙面AP":"wall_ap", "网络设备":"network",
    "影音设备":"av", "智能系统":"system", "智能电箱模块":"system", "综合布线":"system", "其他设备":"other",
}
MAJOR_BY_DEVICE_TYPE = {
    "av":"影音", "light":"灯光", "network":"网络", "ceiling_ap":"网络", "wall_ap":"网络",
    "switch":"智能", "curtain":"智能", "sensor":"智能", "water":"智能", "thermostat":"智能",
    "lock":"智能", "camera":"智能", "system":"智能", "other":"智能",
}


def canonical_product_category(value: str) -> str:
    clean = str(value or "").strip()
    if clean in PRODUCT_CATEGORIES:
        return clean
    device_type = LEGACY_TYPE_BY_CATEGORY.get(clean, clean if clean in DEVICE_TYPE_NAMES else "other")
    return MAJOR_BY_DEVICE_TYPE.get(device_type, "智能")


def canonical_device_type(value: str, category: str = "") -> str:
    clean = str(value or "").strip()
    if clean in DEVICE_TYPE_NAMES:
        return clean
    if clean in LEGACY_TYPE_BY_CATEGORY:
        return LEGACY_TYPE_BY_CATEGORY[clean]
    major = canonical_product_category(category)
    return {"影音":"av", "灯光":"light", "网络":"network"}.get(major, "other")


def brand_id(name: str) -> str:
    return uuid.uuid5(uuid.NAMESPACE_URL, "taiyuan-brand:" + name.strip().casefold()).hex


def safe_filename(name: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff-]+", "_", name).strip("_")[:60] or "产品"


def unlink_note(path: Path) -> None:
    try:
        path.unlink()
        return
    except PermissionError:
        try:
            path.chmod(path.stat().st_mode | stat.S_IWRITE)
        except OSError:
            pass
    path.unlink()


def write_note(path: Path, content: str) -> None:
    """Write a note safely on local disks and Windows SMB shares.

    Some Windows NAS clients cannot atomically replace an existing file even
    though creating a new file in the same folder works. Keep the prepared
    file beside its destination, retry transient locks, then use a guarded
    remove-and-rename fallback for shares without overwrite support.
    """
    atomic_write_text(path, content, prefix=".product-", allow_backup_swap=True)


def read_frontmatter(path: Path) -> tuple[dict, str]:
    content = path.read_text(encoding="utf-8-sig")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n?", content, flags=re.S)
    if not match:
        return {}, content
    data = yaml.safe_load(match.group(1)) or {}
    return (data if isinstance(data, dict) else {}), content[match.end():]


def image_name(value: str | None) -> str | None:
    if not value:
        return None
    name = Path(str(value).replace("\\", "/")).name
    return name if re.fullmatch(r"[a-f0-9]{32}\.(?:jpg|jpeg|png|webp)", name) and (IMAGE_DIR / name).is_file() else None


def note_to_product(path: Path) -> dict | None:
    data, _ = read_frontmatter(path)
    pid = str(data.get("id") or "")
    if data.get("类型") != "报价产品" or not re.fullmatch(r"[a-f0-9]{32}", pid):
        return None
    name = str(data.get("产品名称") or path.stem).strip()
    brand = str(data.get("品牌") or "").strip()
    if not name or not brand:
        return None
    try:
        standard = int(data.get("售价_分", 0))
        raw_cost = data.get("进货价_分")
        cost = int(raw_cost) if raw_cost not in (None, "") else None
    except (TypeError, ValueError):
        return None
    if standard < 0 or (cost is not None and cost < 0):
        return None
    raw_category = str(data.get("分类") or "智能").strip()
    category = canonical_product_category(raw_category)
    device_type = canonical_device_type(data.get("点位类型") or data.get("设备类型") or raw_category, category)
    system_category = "network" if device_type in {"ceiling_ap", "wall_ap"} else canonical_system_category(data.get("所属系统"))
    stored_brand_id = str(data.get("品牌ID") or "").strip()
    if not re.fullmatch(r"[a-f0-9]{32}", stored_brand_id):
        stored_brand_id = brand_id(brand)
    return {
        "id": pid, "brand_id": stored_brand_id, "brand_name": brand,
        "name": name, "series": str(data.get("系列") or ""),
        "model": str(data.get("型号") or ""),
        "category": category,
        "device_type": device_type,
        "system_category": system_category,
        "standard_cents": standard, "cost_cents": cost,
        "unit": str(data.get("单位") or "个"),
        "origin": str(data.get("产地") or ""),
        "params": str(data.get("参数") or ""),
        "description": str(data.get("说明") or ""),
        "image_path": image_name(data.get("图片")),
        "enabled": int(bool(data.get("启用", True))),
        "updated_at": str(data.get("更新时间") or ""),
        "note_path": str(path.relative_to(VAULT_ROOT)),
        "audit_reviewer": str(data.get("审核人") or "待审核"),
    }


class ObsidianProductRepository:
    def __init__(self):
        self._index_lock = threading.RLock()
        self._index: dict[str, tuple[Path, int, int]] = {}
        self._products_by_id: dict[str, dict | None] = {}
        self._parsed: dict[str, tuple[int, int, dict | None]] = {}
        self._inventory_at = 0.0
        self._refreshing_inventory = False
        self._refresh_lock = threading.Lock()
        self._refresh_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="product-index")
        # A catalog walk is the external-change reconciliation pass, not a
        # per-request lookup. Keep the in-memory index warm between sync cycles.
        self._inventory_ttl = 30.0

    @staticmethod
    def _file_key(path: Path) -> str:
        return os.path.normcase(str(path.resolve(strict=False)))

    def _refresh_inventory_background(self) -> None:
        try:
            self._inventory(force=True)
        finally:
            with self._refresh_lock:
                self._refreshing_inventory = False

    def _inventory(self, *, force: bool = False, stale_while_refresh: bool = False) -> dict[str, tuple[Path, int, int]]:
        """Build a cheap metadata index; unchanged notes are never reparsed."""
        now = time.monotonic()
        if not force and stale_while_refresh:
            # This fast path deliberately does not acquire _index_lock: a refresh
            # may be walking SMB while readers continue using the previous map.
            if self._inventory_at and now - self._inventory_at < self._inventory_ttl:
                return self._index
            if self._index:
                with self._refresh_lock:
                    if not self._refreshing_inventory:
                        self._refreshing_inventory = True
                        self._refresh_executor.submit(self._refresh_inventory_background)
                return self._index
        with self._index_lock:
            if not force and self._inventory_at and now - self._inventory_at < self._inventory_ttl:
                return self._index
            if not force and stale_while_refresh and self._index:
                if not self._refreshing_inventory:
                    self._refreshing_inventory = True
                    self._refresh_executor.submit(self._refresh_inventory_background)
                return self._index
            started = time.perf_counter()
            parse_ms = 0.0
            index: dict[str, tuple[Path, int, int]] = {}
            scanned = 0
            parsed_count = 0
            for path in PRODUCT_DIR.rglob("*.md"):
                if any(part.startswith("_") for part in path.relative_to(PRODUCT_DIR).parts[:-1]):
                    continue
                scanned += 1
                try:
                    stat_result = path.stat()
                    key = self._file_key(path)
                    prior = self._parsed.get(key)
                    stamp = (stat_result.st_mtime_ns, stat_result.st_size)
                    if prior and prior[:2] == stamp:
                        product = prior[2]
                    else:
                        parsed_count += 1
                        parse_started = time.perf_counter()
                        try:
                            product = note_to_product(path)
                        except (OSError, UnicodeError, yaml.YAMLError):
                            product = None
                        parse_ms += (time.perf_counter() - parse_started) * 1000
                        self._parsed[key] = (*stamp, product)
                    if product:
                        existing = index.get(product["id"])
                        # A legacy sync may have left two notes with the same ID.
                        # Prefer the authoritative system folder over a stale
                        # legacy copy, then use mtime to break genuine ties.
                        rank = (path.parent.name == SYSTEM_FOLDER_BY_ID[product["system_category"]], stamp[0], str(path))
                        previous = self._parsed.get(self._file_key(existing[0]), (0, 0, None))[2] if existing else None
                        prior_rank = (existing[0].parent.name == SYSTEM_FOLDER_BY_ID[previous["system_category"]], existing[1], str(existing[0])) if previous else (False, 0, "")
                        if not existing or rank > prior_rank:
                            index[product["id"]] = (path, *stamp)
                except OSError:
                    continue
            stale = set(self._parsed) - {self._file_key(path) for path, _, _ in index.values()}
            # Keep non-product markdown out of the parsed cache too, while preserving
            # entries not visited only if an inventory walk failed part-way.
            if scanned >= len(index):
                for key in stale:
                    self._parsed.pop(key, None)
            self._index = index
            self._products_by_id = {
                product_id: self._parsed.get(self._file_key(item[0]), (0, 0, None))[2]
                for product_id, item in index.items()
            }
            self._inventory_at = time.monotonic()
            record_event("vault_scan", operation="index", scope="products", fileCount=scanned,
                         parsedCount=parsed_count,
                         durationMs=round((time.perf_counter()-started)*1000, 2),
                         parseMs=round(parse_ms, 2), success=True)
            return self._index

    def _notes(self):
        inventory = self._inventory(stale_while_refresh=True)
        for path, _, _ in sorted(inventory.values(), key=lambda item: str(item[0])):
            yield path

    def _find(self, product_id: str) -> Path | None:
        if not re.fullmatch(r"[a-f0-9]{32}", product_id):
            return None
        item = self._inventory().get(product_id)
        if not item:
            return None
        path, mtime, size = item
        try:
            current = path.stat()
        except OSError:
            self._inventory(force=True)
            return None
        if current.st_mtime_ns != mtime or current.st_size != size:
            self._inventory(force=True)
            item = self._index.get(product_id)
            return item[0] if item else None
        return path

    def status(self) -> dict:
        notes=[]
        digest=hashlib.sha256()
        for product in self.list(include_disabled=True):
            stamp=f"{product['id']}|{product['updated_at']}|{product['standard_cents']}|{product['category']}|{product['system_category']}"
            digest.update(stamp.encode("utf-8")); notes.append(product)
        return {
            "vault_root": str(VAULT_ROOT), "product_dir": str(PRODUCT_DIR), "image_dir": str(IMAGE_DIR),
            "product_count": len(notes), "catalog_revision": digest.hexdigest()[:12],
            "categories": list(PRODUCT_CATEGORIES),
        }

    def normalize_layout(self) -> int:
        """Move active notes by 所属系统 without rewriting user-maintained content."""
        changed=0
        self._inventory(force=True)
        for product in self.list(include_disabled=True):
            path=self._find(product["id"])
            if not path:
                continue
            target_parent=PRODUCT_DIR/SYSTEM_FOLDER_BY_ID[product["system_category"]]
            if path.parent == target_parent:
                continue
            target_parent.mkdir(parents=True, exist_ok=True)
            target=target_parent/path.name
            if target.exists():
                raise FileExistsError(f"产品分类目标已存在，未覆盖：{target}")
            path.rename(target)
            stat_result=target.stat()
            with self._index_lock:
                self._index[product["id"]]=(target,stat_result.st_mtime_ns,stat_result.st_size)
                self._parsed[self._file_key(target)]=(stat_result.st_mtime_ns,stat_result.st_size,{**product,"note_path":str(target.relative_to(VAULT_ROOT))})
                self._parsed.pop(self._file_key(path),None)
                self._products_by_id[product["id"]]={**product,"note_path":str(target.relative_to(VAULT_ROOT))}
            changed+=1
        return changed

    def list(self, db=None, *, q="", brand_id="", series="", category="", include_disabled=False, refresh=False):
        result = []
        query = q.casefold()
        # Reuse the short-lived inventory between product, brand and quote reads.
        # A forced recursive SMB walk here would make every page visit rescan the
        # entire catalog even when nothing changed.
        inventory = self._inventory(force=refresh, stale_while_refresh=not refresh)
        products_by_id = self._products_by_id
        for product_id in inventory:
            p = products_by_id.get(product_id)
            if not p or (not include_disabled and not p["enabled"]):
                continue
            if query and not any(query in str(p[k]).casefold() for k in ("name", "model", "brand_name")):
                continue
            if brand_id and p["brand_id"] != brand_id:
                continue
            if series and p["series"] != series:
                continue
            if category and p["category"] != category:
                continue
            result.append(p)
        return sorted(result, key=lambda p: (p["brand_name"], p["series"], p["name"]))

    def get(self, db, product_id):
        item = self._inventory().get(product_id)
        if not item:
            return None
        path, mtime, size = item
        try:
            current = path.stat()
            if (current.st_mtime_ns, current.st_size) != (mtime, size):
                self._inventory(force=True)
                item = self._index.get(product_id)
                if not item:
                    return None
                path, mtime, size = item
            key = self._file_key(path)
            with self._index_lock:
                cached = self._parsed.get(key)
                if cached and cached[:2] == (mtime, size):
                    return cached[2]
            self._inventory(force=True)
            with self._index_lock:
                cached = self._parsed.get(key)
                return cached[2] if cached else None
        except (OSError, UnicodeError, yaml.YAMLError):
            return None

    def get_cached(self, product_id):
        """Resolve a product from the already-loaded catalog without SMB I/O.

        Point placement uses this path so a click never starts a catalog walk. The
        catalog index is populated/refreshed by the product library/list request.
        """
        return self._products_by_id.get(product_id)

    def delete(self, product_id: str) -> dict | None:
        """Delete the catalog note. Product images stay available for historical quote snapshots."""
        path = self._find(product_id)
        if not path:
            return None
        product = note_to_product(path)
        unlink_note(path)
        with self._index_lock:
            key = self._file_key(path)
            self._index.pop(product_id, None)
            self._parsed.pop(key, None)
            self._products_by_id.pop(product_id, None)
        return product

    def save(self, product: dict) -> dict:
        pid = product["id"]
        existing_path = self._find(pid)
        previous, body = read_frontmatter(existing_path) if existing_path else ({}, "")
        product["category"] = canonical_product_category(product.get("category", ""))
        product["device_type"] = canonical_device_type(product.get("device_type", ""), product["category"])
        product["system_category"] = "network" if product["device_type"] in {"ceiling_ap", "wall_ap"} else canonical_system_category(product.get("system_category"))
        target_dir = PRODUCT_DIR / SYSTEM_FOLDER_BY_ID[product["system_category"]]
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / ((existing_path.name if existing_path else f"{safe_filename(product['name'])}-{pid[:8]}.md"))
        if path != existing_path and path.exists():
            raise FileExistsError(f"产品分类目标已存在，未覆盖：{path}")
        image = product.get("image_path")
        reviewer = previous.get("审核人") or "待审核"
        meta = dict(previous)
        for obsolete in ("系列", "型号", "设备类型"):
            meta.pop(obsolete, None)
        meta.update({
            "id": pid, "类型": "报价产品", "产品名称": product["name"],
            "型号": product.get("model", ""), "品牌ID": product.get("brand_id") or brand_id(product["brand_name"]),
            "品牌": product["brand_name"], "分类": product["category"],
            "点位类型": product["device_type"],
            "所属系统": product["system_category"],
            "产地": product.get("origin", ""), "单位": product.get("unit", "个"),
            "售价_分": product["standard_cents"], "进货价_分": product.get("cost_cents"),
            "参数": product.get("params", ""), "说明": product.get("description", ""),
            "图片": f"09_附件/产品图片/{image}" if image else "",
            "启用": bool(product.get("enabled", 1)),
            "状态": "在用" if product.get("enabled", 1) else "停用",
            "审核人": reviewer,
            "协议": previous.get("协议") or "",
            "更新时间": product["updated_at"],
        })
        managed = (
            "<!-- pointquote:start -->\n"
            f"# {product['name']}\n\n"
            + ("> [!warning] ⚠️ 待专业审核\n\n" if reviewer == "待审核" else f"> [!success] 已审核：{reviewer}\n\n")
            + (f"![[{image}]]\n\n" if image else "")
            + "## 基本信息\n\n| 项 | 值 |\n| --- | --- |\n"
            + f"| 品牌 | {product['brand_name']} |\n"
            + f"| 型号 | {product.get('model','')} |\n"
            + f"| 分类 | {product['category']} |\n"
            + f"| 所属系统 | {SYSTEM_BY_ID[product['system_category']]['name_zh']} |\n"
            + f"| 适用点位 | {DEVICE_TYPE_NAMES[product['device_type']]} |\n"
            + f"| 产地 | {product.get('origin','')} |\n"
            + f"| 单位 | {product.get('unit','个')} |\n"
            + f"| 售价 | ¥{product['standard_cents']/100:.2f} |\n"
            + (f"| 进货价 | ¥{product['cost_cents']/100:.2f} |\n" if product.get("cost_cents") is not None else "")
            + f"\n## 技术参数\n\n{product.get('params','')}\n\n"
            + f"## 产品说明\n\n{product.get('description','')}\n"
            + "<!-- pointquote:end -->"
        )
        if "<!-- pointquote:start -->" in body and "<!-- pointquote:end -->" in body:
            body = re.sub(r"<!-- pointquote:start -->.*?<!-- pointquote:end -->", lambda _: managed, body, count=1, flags=re.S)
        else:
            body = managed + "\n\n## 功能\n\n## 适用场景\n\n## 关联\n\n- 关联知识：\n- 关联案例：\n" + ("\n" + body if body.strip() else "")
        content = "---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=1000) + "---\n" + body.rstrip() + "\n"
        write_note(path, content)
        saved = note_to_product(path)
        if not saved or saved["id"] != pid or saved["standard_cents"] != product["standard_cents"]:
            raise OSError("产品文件落盘校验失败")
        if existing_path and existing_path != path and existing_path.exists():
            unlink_note(existing_path)
        with self._index_lock:
            key = self._file_key(path)
            stat_result = path.stat()
            self._index[pid] = (path, stat_result.st_mtime_ns, stat_result.st_size)
            self._parsed[key] = (stat_result.st_mtime_ns, stat_result.st_size, saved)
            self._products_by_id[pid] = saved
            self._inventory_at = time.monotonic()
            if existing_path and existing_path != path:
                self._parsed.pop(self._file_key(existing_path), None)
        return saved


product_repository = ObsidianProductRepository()
