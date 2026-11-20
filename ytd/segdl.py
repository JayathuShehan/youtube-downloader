"""Multi-connection segmented HTTP downloader (the "IDM" part).

* Splits the file into byte ranges and downloads them on N connections at once.
* When a connection finishes early it takes half of the largest remaining
  segment, so every connection stays busy until the very end.
* Progress is saved to ``<part>.ytd.json`` so a paused (or killed) download
  continues from where it stopped.
* Expired stream links (HTTP 403/410) are refreshed through a callback.
"""

import json
import os
import threading
import time
from collections import deque

import requests

REQUEST_SIZE = 10 * 1024 * 1024  # bytes per HTTP request; YouTube throttles very long requests
READ_BLOCK = 256 * 1024
MIN_SPLIT = 1024 * 1024          # never split segments smaller than this
MAX_FAILS = 8                    # consecutive failures before a connection gives up
MAX_REFRESHES = 6


class DownloadError(Exception):
    pass


class _UrlExpired(Exception):
    def __init__(self, gen):
        super().__init__("link expired")
        self.gen = gen


class _Seg:
    __slots__ = ("start", "end", "pos", "active")

    def __init__(self, start, end, pos=None):
        self.start = start
        self.end = end          # inclusive
        self.pos = start if pos is None else pos  # next byte to fetch
        self.active = False

    @property
    def remaining(self):
        return max(0, self.end - self.pos + 1)

    @property
    def done_bytes(self):
        return max(0, min(self.pos, self.end + 1) - self.start)


class SegmentedDownload:
    def __init__(self, url, headers, part_path, connections=8, refresher=None):
        self.url = url
        self.headers = dict(headers or {})
        self.part_path = part_path
        self.state_path = part_path + ".ytd.json"
        self.connections = max(1, min(32, int(connections)))
        self.refresher = refresher
        self.size = None
        self.ranges_ok = True
        self.segments = []
        self.lock = threading.Lock()
        self.active = 0
        self.error = None
        self.running = False
        self._url_gen = 0
        self._refreshes = 0
        self._refresh_lock = threading.Lock()
        self._samples = deque()
        self._speed = 0.0
        self._single_done = 0
        self._stop = threading.Event()

    # ------------------------------------------------------------------ info
    @property
    def downloaded(self):
        if not self.ranges_ok:
            return self._single_done
        with self.lock:
            return sum(s.done_bytes for s in self.segments)

    @property
    def complete(self):
        if not self.size:
            return False
        return self.downloaded >= self.size

    def snapshot(self):
        with self.lock:
            segs = [[s.start, s.end, min(s.pos, s.end + 1)] for s in sorted(self.segments, key=lambda s: s.start)]
        return {
            "size": self.size,
            "downloaded": self.downloaded,
            "speed": self._speed if self.running else 0.0,
            "active": self.active,
            "segments": segs,
        }

    # --------------------------------------------------------------- prepare
    def prepare(self):
        """Load saved progress or probe the server and create segments."""
        if self.segments:  # already prepared in this session (resume after pause)
            return
        if self._load_state():
            return
        self._probe()
        if self.ranges_ok and self.size:
            n = max(1, min(self.connections, self.size // MIN_SPLIT or 1))
            step = -(-self.size // n)
            self.segments = [_Seg(i, min(i + step, self.size) - 1) for i in range(0, self.size, step)]
            with open(self.part_path, "wb") as f:
                f.truncate(self.size)
            self._save_state()

    def _load_state(self):
        if not (os.path.exists(self.state_path) and os.path.exists(self.part_path)):
            return False
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                st = json.load(f)
            size = int(st["size"])
            if size <= 0 or os.path.getsize(self.part_path) != size:
                return False
            self.size = size
            self.ranges_ok = True
            self.segments = [_Seg(int(a), int(b), int(p)) for a, b, p in st["segments"]]
            return True
        except (OSError, ValueError, KeyError, TypeError):
            return False

    def _save_state(self):
        if not (self.ranges_ok and self.size):
            return
        with self.lock:
            segs = [[s.start, s.end, min(s.pos, s.end + 1)] for s in self.segments]
        tmp = self.state_path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"size": self.size, "segments": segs}, f)
            os.replace(tmp, self.state_path)
        except OSError:
            pass

    def _probe(self):
        last = None
        for attempt in range(4):
            gen = self._url_gen
            try:
                r = requests.get(self.url, headers={**self.headers, "Range": "bytes=0-0"}, stream=True, timeout=20)
                try:
                    if r.status_code in (403, 410):
                        self._refresh(gen)
                        continue
                    if r.status_code == 206:
                        total = (r.headers.get("Content-Range") or "").rsplit("/", 1)[-1]
                        if total.isdigit():
                            self.size = int(total)
                            self.ranges_ok = True
                            return
                    if r.status_code in (200, 206):
                        length = r.headers.get("Content-Length")
                        self.size = int(length) if length and length.isdigit() and r.status_code == 200 else None
                        self.ranges_ok = False
                        return
                    raise DownloadError(f"Server answered HTTP {r.status_code}")
                finally:
                    r.close()
            except requests.RequestException as e:
                last = e
                time.sleep(1 + attempt)
        raise DownloadError(f"Could not connect: {last}" if last else "Could not get the stream link.")

    def _refresh(self, gen):
        with self._refresh_lock:
            if gen != self._url_gen:
                return  # another connection already refreshed it
            if not self.refresher:
                raise DownloadError("Stream link expired (HTTP 403).")
            self._refreshes += 1
            if self._refreshes > MAX_REFRESHES:
                raise DownloadError("YouTube keeps refusing the stream (HTTP 403). Try fewer connections.")
            url, headers = self.refresher()
            self.url = url
            if headers:
                self.headers = dict(headers)
            self._url_gen += 1

    # ------------------------------------------------------------------- run
    def run(self, stop_event):
        """Blocking. Returns 'done' or 'paused'; raises DownloadError on failure."""
        self._stop = stop_event
        self.error = None
        self.running = True
        self._samples.clear()
        try:
            if not (self.ranges_ok and self.size):
                return self._run_single()
            if not self.complete:
                workers = [threading.Thread(target=self._worker, daemon=True) for _ in range(self.connections)]
                for w in workers:
                    w.start()
                last_save = time.monotonic()
                while any(w.is_alive() for w in workers):
                    time.sleep(0.25)
                    self._sample()
                    if time.monotonic() - last_save >= 1.0:
                        self._save_state()
                        last_save = time.monotonic()
                for w in workers:
                    w.join()
            self._save_state()
            if self.complete:
                # The state file is removed by the job after merging, so a crash
                # during merging does not force a re-download.
                return "done"
            if self._stop.is_set():
                return "paused"
            raise DownloadError(self.error or "Download failed.")
        finally:
            self.running = False
            self._speed = 0.0

    def _sample(self):
        now = time.monotonic()
        self._samples.append((now, self.downloaded))
        while len(self._samples) > 2 and now - self._samples[0][0] > 3.0:
            self._samples.popleft()
        (t0, d0), (t1, d1) = self._samples[0], self._samples[-1]
        self._speed = (d1 - d0) / (t1 - t0) if t1 > t0 else 0.0

    def _take_segment(self):
        with self.lock:
            idle = [s for s in self.segments if not s.active and s.remaining > 0]
            if idle:
                seg = max(idle, key=lambda s: s.remaining)
                seg.active = True
                return seg
            busy = [s for s in self.segments if s.active and s.remaining >= 2 * MIN_SPLIT]
            if not busy:
                return None
            victim = max(busy, key=lambda s: s.remaining)
            mid = victim.pos + victim.remaining // 2
            new = _Seg(mid, victim.end)
            victim.end = mid - 1
            new.active = True
            self.segments.append(new)
            return new

    def _worker(self):
        fails = 0
        sess = requests.Session()
        try:
            fh = open(self.part_path, "r+b", buffering=0)
        except OSError as e:
            self.error = f"Cannot write file: {e}"
            return
        try:
            while not self._stop.is_set():
                seg = self._take_segment()
                if seg is None:
                    return
                with self.lock:
                    self.active += 1
                try:
                    self._fetch(sess, fh, seg)
                    fails = 0
                except _UrlExpired as e:
                    fails += 1
                    try:
                        self._refresh(e.gen)
                    except Exception as err:  # noqa: BLE001
                        self.error = str(err)
                        return
                except (requests.RequestException, DownloadError, OSError) as e:
                    fails += 1
                    self.error = str(e)
                    if fails >= MAX_FAILS:
                        return
                    self._stop.wait(min(2 ** fails, 10))
                finally:
                    with self.lock:
                        seg.active = False
                        self.active -= 1
        finally:
            fh.close()
            sess.close()

    def _fetch(self, sess, fh, seg):
        empty_responses = 0
        while not self._stop.is_set():
            with self.lock:
                pos, end = seg.pos, seg.end
            if pos > end:
                return
            req_end = min(end, pos + REQUEST_SIZE - 1)
            gen = self._url_gen
            r = sess.get(self.url, headers={**self.headers, "Range": f"bytes={pos}-{req_end}"},
                         stream=True, timeout=(15, 30))
            got = 0
            try:
                if r.status_code in (403, 410):
                    raise _UrlExpired(gen)
                if r.status_code != 206:
                    raise DownloadError(f"Server answered HTTP {r.status_code}")
                for block in r.iter_content(READ_BLOCK):
                    if self._stop.is_set():
                        return
                    with self.lock:
                        pos, end = seg.pos, seg.end
                    if pos > end:
                        return  # another connection took over the rest
                    block = block[: end - pos + 1]
                    fh.seek(pos)
                    view = memoryview(block)
                    while view:
                        n = fh.write(view)
                        view = view[n:]
                    with self.lock:
                        seg.pos = pos + len(block)
                    got += len(block)
            finally:
                r.close()
            if got == 0:
                empty_responses += 1
                if empty_responses >= 3:
                    raise DownloadError("Server sent no data.")

    def _run_single(self):
        """Fallback for servers without range support: one connection, restarts on resume."""
        self._single_done = 0
        r = requests.get(self.url, headers=self.headers, stream=True, timeout=(15, 30))
        try:
            if r.status_code != 200:
                raise DownloadError(f"Server answered HTTP {r.status_code}")
            self.active = 1
            with open(self.part_path, "wb") as f:
                for block in r.iter_content(READ_BLOCK):
                    if self._stop.is_set():
                        return "paused"
                    f.write(block)
                    self._single_done += len(block)
                    self._sample()
            if not self.size:
                self.size = self._single_done
            return "done"
        finally:
            self.active = 0
            r.close()
