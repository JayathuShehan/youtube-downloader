"""Small shared helpers."""

import os
import re
import sys


def resource_path(*parts):
    """Path to a bundled resource (works from source and from a PyInstaller exe)."""
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def app_dir():
    """Folder that holds YTDownloader.exe (or the project root when run from source)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def default_download_dir():
    path = os.path.join(os.path.expanduser("~"), "Downloads")
    return path if os.path.isdir(path) else os.path.expanduser("~")


def fmt_bytes(n):
    if n is None:
        return "?"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def fmt_eta(seconds):
    if seconds is None or seconds < 0 or seconds == float("inf"):
        return "--:--"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def fmt_duration(seconds):
    if not seconds:
        return ""
    return fmt_eta(seconds)


_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def safe_filename(name, max_len=150):
    name = _ILLEGAL.sub("_", name or "video")
    name = re.sub(r"\s+", " ", name).strip().rstrip(". ")
    if not name:
        name = "video"
    if name.upper() in _RESERVED:
        name = f"_{name}"
    return name[:max_len].rstrip(". ")


def unique_path(path):
    if not os.path.exists(path):
        return path
    root, ext = os.path.splitext(path)
    i = 1
    while os.path.exists(f"{root} ({i}){ext}"):
        i += 1
    return f"{root} ({i}){ext}"
