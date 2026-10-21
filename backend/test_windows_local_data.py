"""A copied Windows tool folder must use only its own data directory."""
from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path


APP_SOURCE = Path(__file__).resolve().parents[1]
LEGACY_ID = "f" * 32


def _run_package(package: Path, phase: str, old_db: Path) -> None:
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(package),
        "POINT_QUOTE_LOCAL_DATA_MODE": "1",
        "POINT_QUOTE_DATA_DIR": str(package.parent / "wrong-data"),
        "POINT_QUOTE_VAULT_ROOT": str(package.parent / "wrong-vault"),
        "POINT_QUOTE_UPLOADS_DIR": str(package.parent / "wrong-uploads"),
        "POINT_QUOTE_LOG_DIR": str(package.parent / "wrong-logs"),
        "POINT_QUOTE_LEGACY_DB": str(old_db),
        "LOCAL_TEST_PHASE": phase,
        "LOCAL_TEST_ROOT": str(package),
        "LOCAL_TEST_LEGACY_ID": LEGACY_ID,
    })
    result = subprocess.run(
        [sys.executable, "-c", _PACKAGE_CHECK], cwd=package, env=env,
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr


_PACKAGE_CHECK = r'''
import io
import json
import os
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from backend.app import app, DB, PATHS, MIGRATION_REPORT
from backend import knowledge_repository

root = Path(os.environ["LOCAL_TEST_ROOT"]).resolve()
data = root / "data"
assert PATHS.local_data_mode and PATHS.data_root == data, (PATHS, data)
assert DB == data / "app.sqlite3"
assert not any(os.environ["POINT_QUOTE_LEGACY_DB"] == item.get("source") for item in MIGRATION_REPORT)
knowledge_repository.sync = lambda db: (_ for _ in ()).throw(AssertionError("Local mode invoked the NAS sync engine"))
client = TestClient(app)

def call(method, url, **kwargs):
    response = client.request(method, url, **kwargs)
    assert response.status_code < 400, (url, response.status_code, response.text)
    return response.json()

assert call("GET", "/api/version")["local_data"] is True

def png():
    output = io.BytesIO()
    Image.new("RGB", (100, 100), "white").save(output, format="PNG")
    return output.getvalue()

assert call("GET", "/api/storage-status")["data_dir"] == str(data)
assert not (data / "01_产品库" / "中控系统" / f"{os.environ['LOCAL_TEST_LEGACY_ID']}.md").exists()

if os.environ["LOCAL_TEST_PHASE"] == "write":
    brand = call("POST", "/api/brands", json={"name": "本地测试品牌"})
    logo = call("POST", f"/api/brands/{brand['id']}/logo",
                files={"file": ("logo.svg", b'<svg xmlns="http://www.w3.org/2000/svg"/>', "image/svg+xml")})
    product = call("POST", "/api/products", json={
        "brand_id": brand["id"], "name": "本地测试开关", "category": "switch",
        "standard_price": "199.00", "unit": "个",
    })
    edited_product = call("PUT", f"/api/products/{product['id']}", json={
        "brand_id": product["brand_id"], "name": "本地已修改开关", "category": "switch",
        "standard_price": "229.00", "unit": "个",
    })
    assert edited_product["name"] == "本地已修改开关"
    product = edited_product
    product = call("POST", f"/api/products/{product['id']}/image",
                   files={"file": ("product.png", png(), "image/png")})
    project = call("POST", "/api/projects", json={"name": "本地测试项目"})
    drawing = call("POST", f"/api/projects/{project['id']}/drawings",
                   files={"file": ("drawing.png", png(), "image/png")})
    call("POST", f"/api/projects/{project['id']}/quote-items",
         json={"product_id": product["id"], "quantity": 2, "actual_price": "180.00"})
    sync_status = call("GET", "/api/knowledge-sync/status")
    assert sync_status["sync_status"] == "local" and sync_status["conflicts"] == [], sync_status
    assert sync_status["brand_notes"] >= 1 and sync_status["project_notes"] >= 1, sync_status
    assert list((data / "01_产品库" / "_品牌").glob("*.md"))
    assert list((data / "01_产品库").rglob(f"*{product['id'][:8]}.md"))
    assert list((data / "06_客户档案" / "智能图纸与报价").glob(f"*{project['id'][:8]}.md"))
    assert (data / "09_附件" / "品牌Logo" / logo["logo_path"]).is_file()
    assert (data / "09_附件" / "产品图片" / product["image_path"]).is_file()
    assert (data / "uploads" / drawing["source_path"]).is_file()
    (root / "check-ids.json").write_text(json.dumps({
        "brand": brand["id"], "product": product["id"], "project": project["id"],
        "logo": logo["logo_path"], "image": product["image_path"],
        "drawing": drawing["source_path"],
    }), encoding="utf-8")
else:
    saved = json.loads((root / "check-ids.json").read_text(encoding="utf-8"))
    assert saved["project"] in {item["id"] for item in call("GET", "/api/projects")}
    assert saved["product"] in {item["id"] for item in call("GET", "/api/products")}
    assert next(item for item in call("GET", "/api/products") if item["id"] == saved["product"])["name"] == "本地已修改开关"
    assert saved["brand"] in {item["id"] for item in call("GET", "/api/brands")}
    assert os.environ["LOCAL_TEST_LEGACY_ID"] not in {item["id"] for item in call("GET", "/api/products")}
    project = call("GET", f"/api/projects/{saved['project']}")
    assert project["drawings"] and project["drawings"][0]["source_path"] == saved["drawing"]
    quote = call("GET", f"/api/projects/{saved['project']}/quote")
    assert quote["total"] == "360.00", quote
    for url in (f"/api/brand-files/{saved['logo']}", f"/api/files/{saved['image']}",
                f"/api/files/{saved['drawing']}"):
        assert client.get(url).status_code == 200, url
    export = client.get(f"/api/projects/{saved['project']}/quote/export.xlsx")
    assert export.status_code == 200 and len(export.content) > 1000
    call("PATCH", f"/api/projects/{saved['project']}",
         json={"name": "本地测试项目", "customer": "本地修改"})
    sync_status = call("POST", "/api/knowledge-sync/retry")
    assert sync_status["sync_status"] == "local" and sync_status["conflicts"] == [], sync_status
    note = next((data / "06_客户档案" / "智能图纸与报价").glob(f"*{saved['project'][:8]}.md"))
    assert "本地修改" in note.read_text(encoding="utf-8")
'''


def test_windows_local_data_rebuild_and_offline_business_flow() -> None:
    with tempfile.TemporaryDirectory(prefix="point-quote-local-") as temporary:
        base = Path(temporary).resolve()
        package = base / "movable-tool"
        backend = package / "backend"
        backend.mkdir(parents=True)
        for source in (APP_SOURCE / "backend").glob("*.py"):
            if not source.name.startswith("test_"):
                shutil.copy2(source, backend / source.name)
        shutil.copytree(APP_SOURCE / "assets", package / "assets")
        shutil.copytree(APP_SOURCE / "frontend" / "dist", package / "frontend" / "dist")
        shutil.copy2(APP_SOURCE / "VERSION", package / "VERSION")
        incomplete = subprocess.run(
            [sys.executable, "-c", "import backend.app"], cwd=package,
            env={**os.environ, "PYTHONPATH": str(package), "POINT_QUOTE_LOCAL_DATA_MODE": "1"},
            capture_output=True, text=True, timeout=30,
        )
        assert incomplete.returncode != 0 and "本地 data/ 知识库不完整" in incomplete.stderr
        assert not (package / "data").exists()
        for relative in ("01_产品库/_品牌", "06_客户档案/智能图纸与报价",
                         "09_附件/产品图片", "09_附件/品牌Logo", "uploads"):
            (package / "data" / relative).mkdir(parents=True)

        old_db = base / "old-machine" / "catalog.sqlite3"
        old_db.parent.mkdir()
        with closing(sqlite3.connect(old_db)) as db, db:
            db.executescript("""
                CREATE TABLE brands(id TEXT, name TEXT);
                CREATE TABLE products(id TEXT, brand_id TEXT, name TEXT, category TEXT,
                    standard_cents INTEGER, enabled INTEGER);
            """)
            db.execute("INSERT INTO brands VALUES('old', '旧机器品牌')")
            db.execute("INSERT INTO products VALUES(?, 'old', '不应导入的产品', 'switch', 100, 1)", (LEGACY_ID,))

        _run_package(package, "write", old_db)
        (package / "data" / "app.sqlite3").unlink()
        moved = base / "other-drive" / "copied-tool"
        moved.parent.mkdir()
        package.rename(moved)
        _run_package(moved, "restore", old_db)
        assert not any((base / name).exists() for name in ("wrong-data", "wrong-vault", "wrong-uploads", "wrong-logs"))
