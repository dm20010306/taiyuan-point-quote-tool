"""Resolve business paths from a movable local tool root or the legacy checkout."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping


@dataclass(frozen=True)
class AppPaths:
    app_root: Path
    runtime_root: Path
    data_root: Path
    knowledge_root: Path
    config_root: Path
    backup_root: Path
    uploads_root: Path
    exports_root: Path
    log_root: Path

    local_data_mode: bool

    def resolve_data_path(self, relative: str) -> Path:
        return _resolve_below(self.data_root, relative)

    def resolve_asset_path(self, relative: str) -> Path:
        return _resolve_below(self.knowledge_root / "09_附件", relative)

    def resolve_project_path(self, relative: str) -> Path:
        return _resolve_below(self.knowledge_root / "06_客户档案" / "智能图纸与报价", relative)

    def resolve_product_path(self, relative: str) -> Path:
        return _resolve_below(self.knowledge_root / "01_产品库", relative)

    def resolve_app_asset(self, relative: str) -> Path:
        return _resolve_below(self.app_root / "assets", relative)

    def to_relative_data_path(self, path: Path) -> str:
        try:
            relative = path.resolve().relative_to(self.data_root.resolve())
        except ValueError as error:
            raise ValueError("path is outside the local data root") from error
        return relative.as_posix()


def normalize_relative_path(value: str) -> str:
    """Return a slash-separated relative path, rejecting absolute and parent paths."""
    clean = str(value).replace("\\", "/").strip()
    if not clean or "\x00" in clean or clean.startswith("/") or re.match(r"^[A-Za-z]:", clean):
        raise ValueError("business paths must be relative to the package")
    parts = PurePosixPath(clean).parts
    if not parts or ".." in parts:
        raise ValueError("business path escapes its root")
    return PurePosixPath(*parts).as_posix()


def _resolve_below(root: Path, relative: str) -> Path:
    normalized = normalize_relative_path(relative)
    candidate = root.joinpath(*PurePosixPath(normalized).parts).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError("business path escapes its root")
    return candidate


def get_paths(
    module_file: str | Path = __file__,
    environ: Mapping[str, str] | None = None,
    *,
    platform_name: str | None = None,
) -> AppPaths:
    app_root = Path(module_file).resolve().parents[1]
    env = os.environ if environ is None else environ
    configured_data_root = env.get("POINT_QUOTE_USER_DATA_DIR")
    if configured_data_root:
        data_root = Path(configured_data_root).expanduser()
        if not data_root.is_absolute():
            raise ValueError("POINT_QUOTE_USER_DATA_DIR must be an absolute local path")
        data_root = data_root.resolve()
    else:
        # Keep direct test/development imports portable. The official Mac and
        # Windows launchers always provide a stable per-user data directory.
        data_root = app_root / "data"
    return AppPaths(
        app_root=app_root, runtime_root=app_root, data_root=data_root,
        knowledge_root=data_root, config_root=app_root / "config",
        backup_root=data_root / "backups", uploads_root=data_root / "uploads",
        exports_root=data_root / "exports", log_root=data_root / "logs",
        local_data_mode=True,
    )
