# worldedit_tab/common/recent_paths.py
"""
Remembers the last folder used for each kind of file dialog (texture
folder, palette JSON, source image, etc.) so the next time a file dialog
opens, it starts where you left off instead of some default location.
Persisted to a small JSON file in the user's home directory so it
survives between runs of the app, not just within one session.

Two levels of memory:
  * remember()/get_dir() -- just the folder, like before.
  * remember_file()/get_initial_file_args() -- the exact file, so the
    dialog can pre-select it (not just open in the right folder). Falls
    back to folder-only if the exact file's gone or was never recorded.

Usage:
    from ..common.recent_paths import get_dir, remember, remember_file, get_initial_file_args

    initial = get_dir("texture_folder")
    path = filedialog.askdirectory(initialdir=initial)
    if path:
        remember("texture_folder", path)

    path = filedialog.askopenfilename(**get_initial_file_args("palette_json"))
    if path:
        remember_file("palette_json", path)
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


def _save(data: dict) -> None:
    try:
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass  # best-effort -- never let this break a file dialog


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
    _save(data)


def remember_file(key: str, path: str) -> None:
    """Like remember(), but also records the exact file so a future
    get_initial_file_args() call can pre-select it, not just open its
    folder."""
    if not path:
        return
    remember(key, path)
    data = _load()
    data[f"{key}__file"] = path
    _save(data)


def get_initial_file_args(key: str) -> dict:
    """Returns kwargs to spread into filedialog.askopenfilename()/
    asksaveasfilename(): {"initialdir": ..., "initialfile": ...} with the
    exact last-used file pre-selected, if it still exists -- otherwise
    just {"initialdir": ...} from the last-used folder (get_dir()'s
    normal behavior)."""
    path = _load().get(f"{key}__file")
    if path and os.path.isfile(path):
        return {"initialdir": os.path.dirname(path), "initialfile": os.path.basename(path)}
    return {"initialdir": get_dir(key)}
