"""Read-only existence checks against PyPI and npm, cached on disk.

This tool only *reads* public registry metadata. It never registers,
reserves, or publishes any package name.
"""
import json
import re
import threading
from pathlib import Path

import requests

CACHE_FILE = Path(__file__).resolve().parent.parent / "results" / "registry_cache.json"
_lock = threading.Lock()
_cache = json.loads(CACHE_FILE.read_text()) if CACHE_FILE.exists() else {}
_session = requests.Session()


def _normalize_pypi(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def _fetch(url):
    for _ in range(3):
        try:
            r = _session.get(url, timeout=20)
            if r.status_code == 404:
                return False
            if r.ok:
                return True
        except requests.RequestException:
            pass
    return None  # unknown: network failure, excluded from stats


def exists(name, lang):
    if lang == "python":
        key = "pypi:" + _normalize_pypi(name)
        url = f"https://pypi.org/pypi/{_normalize_pypi(name)}/json"
    else:
        key = "npm:" + name
        url = "https://registry.npmjs.org/" + name.replace("/", "%2F")
    with _lock:
        if key in _cache:
            return _cache[key]
    result = _fetch(url)
    with _lock:
        if result is not None:
            _cache[key] = result
    return result


def save():
    with _lock:
        CACHE_FILE.write_text(json.dumps(_cache, indent=0, sort_keys=True))
