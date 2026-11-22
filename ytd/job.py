"""One download job: fetch info -> download streams in parallel -> merge/convert."""

import itertools
import os
import threading
import time

from . import extractor, ffmpeg
from .extractor import ExtractError
from .ffmpeg import FFmpegError
from .segdl import DownloadError, SegmentedDownload
from .util import safe_filename, unique_path

_ids = itertools.count(1)


class Job:
    def __init__(self, url, kind, quality, folder, connections=8, info=None, cookies=None):
        self.id = str(next(_ids))
        self.cookies = cookies
        self.url = url
        self.kind = kind
        self.quality = quality
        self.folder = os.path.abspath(os.path.expanduser(folder))
        self.connections = connections
        self.info = info
        self.state = "queued"      # queued, fetching, downloading, paused, processing, done, error
        self.stage = "Waiting"
        self.error = None
        self.output = None
        self.quality_label = quality
        self.process_progress = 0.0
        self.created = time.time()
        self.downloads = []        # [(stream, SegmentedDownload)]
        self.output_spec = None
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- control
    @property
    def title(self):
        return (self.info or {}).get("title") or self.url

    @property
    def alive(self):
        return bool(self._thread and self._thread.is_alive())

    def start(self):
        with self._lock:
            if self.alive or self.state in ("done", "processing"):
                return False
            self._stop.clear()
            self.error = None
            self.state = "queued"
            self.stage = "Starting"
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            return True

    def pause(self):
        if self.state in ("queued", "fetching", "downloading"):
            self._stop.set()
            self.stage = "Pausing..."
            return True
        return False

    def resume(self):
        if self.state in ("paused", "error"):
            return self.start()
        return False

    def wait(self, timeout=None):
        if self._thread:
            self._thread.join(timeout)

    # -------------------------------------------------------------------- run
    def _run(self):
        try:
            self._do_run()
        except (ExtractError, DownloadError, FFmpegError) as e:
            self._fail(str(e))
        except OSError as e:
            self._fail(f"File error: {e}")
        except Exception as e:  # noqa: BLE001
            self._fail(f"Unexpected error: {e!r}")

    def _fail(self, msg):
        self._stop.set()
        self.state = "error"
        self.stage = "Failed"
        self.error = msg

    def _paused(self):
        self.state = "paused"
        self.stage = "Paused"

    def _do_run(self):
        if self.info is None:
            self.state = "fetching"
            self.stage = "Getting video info"
            self.info = extractor.fetch_info(self.url, self.cookies)
        if self._stop.is_set():
            return self._paused()

        streams, out = extractor.select(self.info, self.kind, self.quality)
        self.output_spec = out
        self.quality_label = out["label"]
        os.makedirs(self.folder, exist_ok=True)

        if not self.downloads:
            base = safe_filename(self.title, 120)
            vid = safe_filename(str(self.info.get("id") or "x"), 40)
            page = self.info.get("webpage_url") or self.url
            for s in streams:
                part = os.path.join(self.folder, f"{base} [{vid}].f{safe_filename(s['format_id'])}.part")
                refresher = (lambda fid=s["format_id"]: extractor.refresh_stream_url(page, fid, self.cookies))
                dl = SegmentedDownload(s["url"], s["headers"], part, self.connections, refresher)
                self.downloads.append((s, dl))

        self.state = "downloading"
        roles = " + ".join(s["role"] for s, _ in self.downloads)
        self.stage = f"Downloading {roles} ({self.quality_label})"
        for _, dl in self.downloads:
            dl.prepare()
            if self._stop.is_set():
                return self._paused()

        results = {}

        def runner(key, dl):
            try:
                results[key] = dl.run(self._stop)
            except Exception as e:  # noqa: BLE001
                results[key] = e
                self._stop.set()  # stop the other stream too

        threads = [threading.Thread(target=runner, args=(i, dl), daemon=True)
                   for i, (_, dl) in enumerate(self.downloads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        errors = [r for r in results.values() if isinstance(r, Exception)]
        if errors:
            raise errors[0]
        if any(r != "done" for r in results.values()):
            return self._paused()

        self._process()

    def _process(self):
        out = self.output_spec
        self.state = "processing"
        self.process_progress = 0.0
        duration = self.info.get("duration")
        base = safe_filename(self.title, 120)
        final = unique_path(os.path.join(self.folder, f"{base}.{out['ext']}"))
        parts = {s["role"]: dl.part_path for s, dl in self.downloads}

        def prog(p):
            self.process_progress = p

        if out["mode"] == "merge":
            self.stage = "Merging video and audio"
            try:
                ffmpeg.merge(parts["video"], parts["audio"], final, duration, prog)
            except FFmpegError:
                # Some codec combinations do not fit in .mp4; .mkv takes anything.
                self._remove(final)
                final = unique_path(os.path.join(self.folder, f"{base}.mkv"))
                ffmpeg.merge(parts["video"], parts["audio"], final, duration, prog)
        elif out["mode"] == "mp3":
            self.stage = f"Converting to MP3 {out['bitrate']} kbps"
            ffmpeg.to_mp3(parts["audio"], final, out["bitrate"], duration, prog)
        else:
            self.stage = "Finishing file"
            src = next(iter(parts.values()))
            ffmpeg.remux(src, final, duration, prog)

        for p in parts.values():
            self._remove(p)
            self._remove(p + ".ytd.json")
        self.output = final
        self.state = "done"
        self.stage = "Completed"

    @staticmethod
    def _remove(path):
        try:
            os.remove(path)
        except OSError:
            pass

    # --------------------------------------------------------------- snapshot
    def snapshot(self):
        streams = []
        total = downloaded = 0
        speed = 0.0
        active = 0
        for s, dl in self.downloads:
            snap = dl.snapshot()
            size = snap["size"] or s.get("size") or s.get("est_size") or 0
            total += size
            downloaded += snap["downloaded"]
            speed += snap["speed"]
            active += snap["active"]
            streams.append({
                "role": s["role"],
                "size": size,
                "downloaded": snap["downloaded"],
                "speed": snap["speed"],
                "active": snap["active"],
                "segments": snap["segments"],
            })
        if self.state == "done":
            percent = 100.0
        elif total:
            percent = min(100.0, downloaded * 100.0 / total)
        else:
            percent = 0.0
        remaining = max(0, total - downloaded)
        eta = remaining / speed if speed > 0 else None
        info = self.info or {}
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "thumbnail": info.get("thumbnail"),
            "kind": self.kind,
            "quality": self.quality_label,
            "folder": self.folder,
            "state": self.state,
            "stage": self.stage,
            "error": self.error,
            "output": self.output,
            "total": total,
            "downloaded": downloaded,
            "percent": round(percent, 2),
            "speed": speed,
            "eta": eta,
            "connections": active,
            "max_connections": self.connections,
            "process_progress": round(self.process_progress * 100, 1),
            "streams": streams,
            "created": self.created,
        }
