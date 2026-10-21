"""Small, local-only diagnostic logger for API, SMB and vault operations."""
from __future__ import annotations

import contextvars
import errno
import json
import os
import sqlite3
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any
from backend.path_resolver import get_paths


PATHS = get_paths(__file__)
APP_ROOT = PATHS.app_root
DATA_ROOT = PATHS.data_root
LOG_DIR = PATHS.log_root
LOG_FILE = LOG_DIR / "diagnostics.jsonl"
_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("pointquote_request_id", default="")
_write_lock = threading.Lock()


def set_request_id(value: str):
    return _request_id.set(value)


def reset_request_id(token) -> None:
    _request_id.reset(token)


def current_request_id() -> str:
    return _request_id.get()


def classify_error(error: BaseException, operation: str = "") -> str:
    message = str(error).casefold()
    winerror = getattr(error, "winerror", None)
    if isinstance(error, FileNotFoundError):
        return "FILE_NOT_FOUND"
    if isinstance(error, PermissionError):
        return "PERMISSION_DENIED"
    if isinstance(error, TimeoutError) or winerror in {53, 64, 121, 1231} or "timed out" in message:
        return "SMB_TIMEOUT"
    if winerror in {32, 33} or "being used by another process" in message or "文件正在被另一个进程使用" in message:
        return "FILE_LOCKED"
    if isinstance(error, sqlite3.OperationalError) and ("locked" in message or "busy" in message):
        return "CONCURRENT_WRITE"
    if isinstance(error, json.JSONDecodeError):
        return "JSON_PARSE_ERROR"
    if "yaml" in type(error).__module__.casefold() or "markdown" in message:
        return "MARKDOWN_PARSE_ERROR"
    if isinstance(error, OSError) and (getattr(error, "errno", None) in {errno.EINVAL, errno.ENAMETOOLONG} or winerror in {3, 123, 161}):
        return "PATH_INVALID"
    if operation == "rename":
        return "RENAME_FAILED"
    if operation == "write":
        return "WRITE_FAILED"
    if "conflict" in message or "冲突" in message:
        return "SYNC_CONFLICT"
    return "UNKNOWN_ERROR"


def _rotate_if_needed() -> None:
    if LOG_FILE.is_file() and LOG_FILE.stat().st_size > 5 * 1024 * 1024:
        previous = LOG_FILE.with_suffix(".previous.jsonl")
        if previous.exists():
            previous.unlink()
        os.replace(LOG_FILE, previous)


def record_event(event: str, **fields: Any) -> None:
    """Append one JSON line. Diagnostic logging must never break business work."""
    payload = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="milliseconds"),
        "requestId": fields.pop("requestId", None) or current_request_id() or None,
        "event": event,
        **fields,
    }
    try:
        with _write_lock:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            _rotate_if_needed()
            with LOG_FILE.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def record_exception(event: str, error: BaseException, *, operation: str = "", **fields: Any) -> str:
    error_type = classify_error(error, operation)
    record_event(
        event,
        success=False,
        operation=operation or fields.pop("operation", ""),
        errorType=error_type,
        errorMessage=str(error),
        stackTrace="".join(traceback.format_exception(type(error), error, error.__traceback__)),
        **fields,
    )
    return error_type
