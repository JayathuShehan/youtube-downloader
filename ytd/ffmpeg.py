"""Locate and run ffmpeg for merging/converting."""

import os
import shutil
import subprocess
import sys

from .util import app_dir


class FFmpegError(Exception):
    pass


def find_ffmpeg():
    local = os.path.join(app_dir(), "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    if os.path.isfile(local):
        return local
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise FFmpegError(
        "ffmpeg was not found. Put ffmpeg.exe next to YTDownloader.exe, "
        "or install it with:  winget install Gyan.FFmpeg"
    )


def _run(args, duration=None, on_progress=None):
    exe = find_ffmpeg()
    cmd = [exe, "-y", "-hide_banner", "-loglevel", "error", "-nostdin", "-progress", "pipe:1", *args]
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            encoding="utf-8", errors="replace", creationflags=flags)
    for line in proc.stdout:
        if on_progress and duration and line.startswith("out_time_us="):
            value = line.split("=", 1)[1].strip()
            if value.isdigit():
                on_progress(min(1.0, int(value) / 1e6 / duration))
    err = proc.stderr.read()
    proc.wait()
    if proc.returncode != 0:
        raise FFmpegError((err or "ffmpeg failed").strip().splitlines()[-1])
    if on_progress:
        on_progress(1.0)


def merge(video, audio, out, duration=None, on_progress=None):
    args = ["-i", video, "-i", audio, "-map", "0:v:0", "-map", "1:a:0", "-c", "copy"]
    if out.lower().endswith(".mp4"):
        args += ["-movflags", "+faststart"]
    _run([*args, out], duration, on_progress)


def remux(src, out, duration=None, on_progress=None):
    args = ["-i", src, "-c", "copy"]
    if out.lower().endswith((".mp4", ".m4a")):
        args += ["-movflags", "+faststart"]
    _run([*args, out], duration, on_progress)


def to_mp3(src, out, bitrate, duration=None, on_progress=None):
    _run(["-i", src, "-vn", "-ac", "2", "-c:a", "libmp3lame", "-b:a", f"{int(bitrate)}k", out], duration, on_progress)
