# worldedit_tab/common/recent_paths.py
"""
Remembers the last folder used for each kind of file dialog (texture
folder, palette JSON, source image, etc.) so the next time a file dialog
opens, it starts where you left off instead of some default location.
Persisted to a small JSON file in the user's home directory so it
survives between runs of the app, not just within one session.

Usage:
    from ..common.recent_paths import get_dir, remember

    initial = get_dir("texture_folder")
    path = filedialog.askdirectory(initialdir=initial)
    if path:
        remember("texture_folder", path)
"""

import json
import os

_CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".worldedit_tab_recent_paths.json")
_cache = None


def _load() -> dict:
    global _cache
    if _cache is None:
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                _cache = json.load(f)
        except Exception:
            _cache = {}
    return _cache


def get_dir(key: str, default: str = None) -> str:
    """Return the last-remembered directory for `key`, or `default` (falls
    back to the user's home directory) if nothing's been remembered yet or
    the remembered path no longer exists."""
    value = _load().get(key)
    if value and os.path.isdir(value):
        return value
    return default if default is not None else os.path.expanduser("~")


def remember(key: str, path: str) -> None:
    """Record the directory containing `path` (or `path` itself, if it's
    already a directory) as the last-used location for `key`."""
    if not path:
        return
    directory = path if os.path.isdir(path) else os.path.dirname(path)
    if not directory:
        return
    data = _load()
    data[key] = directory
    try:
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass  # best-effort -- never let this break a file dialog
