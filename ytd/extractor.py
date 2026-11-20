"""yt-dlp wrapper: fetch video info, list qualities, pick the streams to download.

yt-dlp is only used to *find* the stream URLs. The transfer itself is done by
our own multi-connection downloader (segdl.py).
"""

import contextlib
import io
import shutil

import yt_dlp

from .util import fmt_bytes


class ExtractError(Exception):
    pass


class _QuietLogger:
    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


def _js_runtimes():
    # YouTube needs a JavaScript runtime to solve its "n" challenge.
    found = {name: {} for name in ("deno", "node", "bun") if shutil.which(name)}
    return found or {"deno": {}}


def _ydl_opts():
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "logger": _QuietLogger(),
        "js_runtimes": _js_runtimes(),
    }


def _clean_error(exc):
    msg = str(exc)
    if msg.startswith("ERROR: "):
        msg = msg[7:]
    # Strip the "[youtube] id: " prefix
    if msg.startswith("[") and "]" in msg:
        msg = msg.split("]", 1)[1].strip()
        if ": " in msg[:20]:
            msg = msg.split(": ", 1)[1]
    return msg


def fetch_info(url):
    url = (url or "").strip()
    if not url:
        raise ExtractError("Please enter a link.")
    try:
        # yt-dlp prints some codec warnings straight to stderr, bypassing the logger.
        with contextlib.redirect_stderr(io.StringIO()), yt_dlp.YoutubeDL(_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        raise ExtractError(_clean_error(e)) from None
    except Exception as e:  # noqa: BLE001 - surface anything as a friendly error
        raise ExtractError(str(e)) from None
    if info.get("_type") == "playlist":
        entries = [e for e in (info.get("entries") or []) if e]
        if not entries:
            raise ExtractError("This looks like a playlist. Paste a link to a single video.")
        info = entries[0]
    if not info.get("formats"):
        raise ExtractError("No downloadable formats were found for this video.")
    return info


# ---------------------------------------------------------------------------
# Format helpers
# ---------------------------------------------------------------------------

def _is_direct(f):
    return f.get("protocol") in ("https", "http") and f.get("url")


def _has_video(f):
    return f.get("vcodec") not in (None, "none") and f.get("height")


def _has_audio(f):
    return f.get("acodec") not in (None, "none")


def _size(f, duration):
    size = f.get("filesize") or f.get("filesize_approx")
    if not size and f.get("tbr") and duration:
        size = f["tbr"] * 1000 / 8 * duration
    return int(size) if size else None


def _codec_rank(vcodec):
    """Lower is better (more compatible inside .mp4)."""
    v = (vcodec or "").lower()
    if v.startswith("avc"):
        return 0
    if v.startswith("vp09") or v.startswith("vp9"):
        return 1
    if v.startswith("av01"):
        return 2
    return 3


def _codec_name(vcodec):
    v = (vcodec or "").lower()
    if v.startswith("avc"):
        return "H.264"
    if v.startswith("vp9") or v.startswith("vp09"):
        return "VP9"
    if v.startswith("av01"):
        return "AV1"
    return v.split(".")[0].upper() or "?"


def _audio_formats(info):
    fmts = [f for f in info["formats"] if _is_direct(f) and _has_audio(f) and not _has_video(f)]
    non_drc = [f for f in fmts if "drc" not in str(f.get("format_id"))]
    return non_drc or fmts


def _best_audio(info, prefer=None):
    fmts = _audio_formats(info)
    if prefer:
        preferred = [f for f in fmts if (f.get("acodec") or "").startswith(prefer)]
        fmts = preferred or fmts
    if not fmts:
        return None
    return max(fmts, key=lambda f: (f.get("abr") or f.get("tbr") or 0))


def _video_groups(info):
    """Group direct video streams by (height, high-fps) and pick the best stream per group."""
    duration = info.get("duration")
    video_only = [f for f in info["formats"] if _is_direct(f) and _has_video(f) and not _has_audio(f)]
    progressive = [f for f in info["formats"] if _is_direct(f) and _has_video(f) and _has_audio(f)]
    groups = {}
    for f in video_only or progressive:
        fps = f.get("fps") or 30
        key = (int(f["height"]), 60 if fps >= 50 else 30)
        groups.setdefault(key, []).append(f)
    result = []
    for (height, fps), fmts in groups.items():
        best = min(fmts, key=lambda f: (_codec_rank(f.get("vcodec")), -(f.get("tbr") or 0)))
        label = f"{height}p" + ("60" if fps == 60 else "")
        result.append({
            "id": label,
            "height": height,
            "fps": fps,
            "format": best,
            "progressive": not video_only,
            "size": _size(best, duration),
        })
    result.sort(key=lambda g: (g["height"], g["fps"]), reverse=True)
    return result


AUDIO_CHOICES = [
    ("m4a", "Best original (M4A / AAC)"),
    ("opus", "Best original (Opus)"),
    ("mp3-320", "MP3 320 kbps"),
    ("mp3-192", "MP3 192 kbps"),
    ("mp3-128", "MP3 128 kbps"),
]


def build_options(info):
    """Everything the UI/CLI needs to show choices."""
    duration = info.get("duration")
    audio_for_video = _best_audio(info, prefer="mp4a")
    a_size = _size(audio_for_video, duration) if audio_for_video else 0

    video = []
    groups = _video_groups(info)
    for g in groups:
        f = g["format"]
        total = (g["size"] or 0) + (0 if g["progressive"] else (a_size or 0))
        label = f"{g['id']}  ({_codec_name(f.get('vcodec'))}, ~{fmt_bytes(total)})"
        video.append({"id": g["id"], "label": label, "size": total or None})
    if video:
        video.insert(0, {"id": "best", "label": f"Best available ({groups[0]['id']})", "size": video[0]["size"]})

    audio = []
    for qid, label in AUDIO_CHOICES:
        if qid == "m4a":
            f = _best_audio(info, prefer="mp4a")
            if not f or not (f.get("acodec") or "").startswith("mp4a"):
                continue
        elif qid == "opus":
            f = _best_audio(info, prefer="opus")
            if not f or not (f.get("acodec") or "").startswith("opus"):
                continue
        else:
            f = _best_audio(info)
            if not f:
                continue
        size = _size(f, duration)
        if qid.startswith("mp3-") and duration:
            size = int(int(qid[4:]) * 1000 / 8 * duration)
        abr = f.get("abr")
        detail = f"{int(abr)} kbps source, " if abr and not qid.startswith("mp3") else ""
        audio.append({"id": qid, "label": f"{label}  ({detail}~{fmt_bytes(size)})", "size": size})

    return {
        "id": info.get("id"),
        "title": info.get("title") or "video",
        "uploader": info.get("uploader") or info.get("channel") or "",
        "duration": duration,
        "thumbnail": info.get("thumbnail"),
        "webpage_url": info.get("webpage_url") or info.get("original_url"),
        "video": video,
        "audio": audio,
    }


def _stream(role, f, duration):
    return {
        "role": role,
        "format_id": f["format_id"],
        "url": f["url"],
        "headers": dict(f.get("http_headers") or {}),
        "size": f.get("filesize") or None,
        "est_size": _size(f, duration),
        "ext": f.get("ext") or "bin",
        "vcodec": f.get("vcodec"),
        "acodec": f.get("acodec"),
    }


def select(info, kind, quality):
    """Return (streams, output) for a given type/quality.

    output = {"ext": ..., "mode": "merge" | "remux" | "mp3", "bitrate": ..., "label": ...}
    """
    duration = info.get("duration")
    if kind == "video":
        groups = _video_groups(info)
        if not groups:
            raise ExtractError("No downloadable video streams found.")
        group = groups[0] if quality in (None, "", "best") else next((g for g in groups if g["id"] == quality), None)
        if group is None:
            raise ExtractError(f"Quality '{quality}' is not available for this video.")
        streams = [_stream("video", group["format"], duration)]
        if group["progressive"]:
            return streams, {"ext": "mp4", "mode": "remux", "label": group["id"]}
        audio = _best_audio(info, prefer="mp4a")
        if not audio:
            raise ExtractError("No audio stream found for this video.")
        streams.append(_stream("audio", audio, duration))
        return streams, {"ext": "mp4", "mode": "merge", "label": group["id"]}

    if kind == "audio":
        quality = quality or "m4a"
        if quality == "m4a":
            f = _best_audio(info, prefer="mp4a")
            out = {"ext": "m4a", "mode": "remux", "label": "M4A"}
        elif quality == "opus":
            f = _best_audio(info, prefer="opus")
            out = {"ext": "opus", "mode": "remux", "label": "Opus"}
        elif quality.startswith("mp3-"):
            f = _best_audio(info)
            out = {"ext": "mp3", "mode": "mp3", "bitrate": int(quality[4:]), "label": f"MP3 {quality[4:]} kbps"}
        else:
            raise ExtractError(f"Unknown audio quality '{quality}'.")
        if not f:
            raise ExtractError("No audio stream found for this video.")
        return [_stream("audio", f, duration)], out

    raise ExtractError(f"Unknown type '{kind}'.")


def refresh_stream_url(webpage_url, format_id):
    """Stream URLs expire after a few hours. Get a fresh one for the same format."""
    info = fetch_info(webpage_url)
    for f in info["formats"]:
        if f.get("format_id") == format_id and f.get("url"):
            return f["url"], dict(f.get("http_headers") or {})
    raise ExtractError(f"Format {format_id} is no longer available.")
