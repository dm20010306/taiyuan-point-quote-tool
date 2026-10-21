"""Serialized, retrying and validated writes for local disks and SMB shares."""
from __future__ import annotations

import os
import stat
import tempfile
import threading
import time
import uuid
from pathlib import Path

from backend.diagnostics import record_event, record_exception


_locks_guard = threading.Lock()
_path_locks: dict[str, threading.Lock] = {}
RETRY_DELAYS = (0.0, 0.5, 1.5)


def _lock_for(path: Path) -> threading.Lock:
    key = os.path.normcase(str(path.resolve(strict=False)))
    with _locks_guard:
        return _path_locks.setdefault(key, threading.Lock())


def atomic_write_text(path: Path, content: str, *, prefix: str = ".pointquote-", allow_backup_swap: bool = False) -> str:
    """Write one complete UTF-8 file while serializing requests for that path.

    Returns ``unchanged`` when an identical save is coalesced, otherwise
    ``written``. Different paths use different locks and may proceed together.
    """
    started = time.perf_counter()
    encoded = content.encode("utf-8")
    lock_started = time.perf_counter()
    with _lock_for(path):
        queue_ms = round((time.perf_counter() - lock_started) * 1000, 2)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if path.is_file() and path.read_bytes() == encoded:
                record_event("vault_write", operation="write", filePath=str(path), durationMs=round((time.perf_counter()-started)*1000,2), queueMs=queue_ms, success=True, deduplicated=True)
                return "unchanged"
        except OSError:
            pass

        descriptor, temporary_name = tempfile.mkstemp(prefix=prefix, suffix=".tmp", dir=path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            if temporary.read_bytes() != encoded:
                raise OSError(f"临时文件校验失败：{path.name}")

            last_error: OSError | None = None
            for attempt, delay in enumerate(RETRY_DELAYS, start=1):
                if delay:
                    time.sleep(delay)
                try:
                    os.replace(temporary, path)
                    if path.read_bytes() != encoded:
                        raise OSError(f"正式文件落盘校验失败：{path.name}")
                    record_event("vault_write", operation="write", filePath=str(path), durationMs=round((time.perf_counter()-started)*1000,2), queueMs=queue_ms, attempts=attempt, success=True)
                    return "written"
                except OSError as error:
                    last_error = error
                    if path.exists():
                        try:
                            path.chmod(path.stat().st_mode | stat.S_IWRITE)
                        except OSError:
                            pass

            if allow_backup_swap and path.exists():
                backup = path.with_name(f".{path.name}.{uuid.uuid4().hex}.bak")
                try:
                    os.replace(path, backup)
                    os.replace(temporary, path)
                    if path.read_bytes() != encoded:
                        raise OSError(f"正式文件落盘校验失败：{path.name}")
                    backup.unlink(missing_ok=True)
                    record_event("vault_write", operation="write", filePath=str(path), durationMs=round((time.perf_counter()-started)*1000,2), queueMs=queue_ms, attempts=len(RETRY_DELAYS)+1, success=True, fallback="backup_swap")
                    return "written"
                except OSError:
                    if backup.exists() and not path.exists():
                        os.replace(backup, path)
                    raise
            if last_error:
                raise last_error
            raise OSError(f"无法写入文件：{path.name}")
        except Exception as error:
            record_exception("vault_write", error, operation="rename" if temporary.exists() else "write", filePath=str(path), durationMs=round((time.perf_counter()-started)*1000,2), queueMs=queue_ms)
            raise
        finally:
            temporary.unlink(missing_ok=True)
