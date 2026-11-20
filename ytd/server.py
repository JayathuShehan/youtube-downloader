"""Local web UI: ytd -ui  ->  http://127.0.0.1:<port>"""

import json
import mimetypes
import os
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import __version__, extractor
from .extractor import ExtractError
from .job import Job
from .util import default_download_dir, resource_path

WEB_DIR = resource_path("ytd", "web")

_jobs = {}
_info_cache = {}
_dialog_lock = threading.Lock()
_settings = {"connections": 8}


def _pick_folder(initial):
    """Open the native Windows folder picker (runs on the request thread)."""
    with _dialog_lock:
        import tkinter
        from tkinter import filedialog

        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            path = filedialog.askdirectory(parent=root, initialdir=initial or default_download_dir(),
                                           title="Select download folder", mustexist=True)
        finally:
            root.destroy()
        return os.path.normpath(path) if path else None


class Handler(BaseHTTPRequestHandler):
    server_version = f"YTDownloader/{__version__}"

    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    # ------------------------------------------------------------ helpers
    def _host_ok(self):
        host = (self.headers.get("Host") or "").split(":")[0].lower()
        return host in ("127.0.0.1", "localhost")

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def _job(self, data):
        job = _jobs.get(str(data.get("job_id")))
        if not job:
            raise LookupError("Unknown download.")
        return job

    # ------------------------------------------------------------- routes
    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {"error": "forbidden"})
        url = urlparse(self.path)
        if url.path == "/api/status":
            job = _jobs.get((parse_qs(url.query).get("job_id") or [""])[0])
            return self._send(200, job.snapshot()) if job else self._send(404, {"error": "Unknown download."})
        if url.path == "/api/jobs":
            jobs = sorted(_jobs.values(), key=lambda j: j.created, reverse=True)
            return self._send(200, {"jobs": [j.snapshot() for j in jobs]})
        if url.path == "/api/config":
            return self._send(200, {"folder": default_download_dir(), "connections": _settings["connections"],
                                    "version": __version__})
        return self._static(url.path)

    def _static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        full = os.path.normpath(os.path.join(WEB_DIR, path.lstrip("/")))
        if not full.startswith(os.path.normpath(WEB_DIR)) or not os.path.isfile(full):
            return self._send(404, b"Not found", "text/plain")
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype.endswith("javascript"):
            ctype += "; charset=utf-8"
        with open(full, "rb") as f:
            self._send(200, f.read(), ctype)

    def do_POST(self):
        if not self._host_ok():
            return self._send(403, {"error": "forbidden"})
        # Only accept JSON: browsers cannot send it cross-site without a CORS preflight we never allow.
        if not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return self._send(415, {"error": "JSON required"})
        try:
            data = self._json_body()
            path = urlparse(self.path).path
            if path == "/api/info":
                url = (data.get("url") or "").strip()
                info = extractor.fetch_info(url)
                _info_cache[url] = info
                return self._send(200, extractor.build_options(info))
            if path == "/api/start":
                url = (data.get("url") or "").strip()
                folder = (data.get("folder") or "").strip() or default_download_dir()
                conns = int(data.get("connections") or _settings["connections"])
                conns = max(1, min(32, conns))
                _settings["connections"] = conns
                kind, quality = data.get("type") or "video", data.get("quality") or "best"
                # Same download already in this session and not finished: reuse it (avoids two jobs on one file).
                for existing in _jobs.values():
                    if (existing.url, existing.kind, existing.quality, existing.folder) == (
                            url, kind, quality, os.path.abspath(folder)) and existing.state not in ("done", "error"):
                        existing.resume()
                        return self._send(200, {"job_id": existing.id})
                job = Job(url, kind, quality, folder, conns, info=_info_cache.get(url))
                _jobs[job.id] = job
                job.start()
                return self._send(200, {"job_id": job.id})
            if path == "/api/pause":
                return self._send(200, {"ok": self._job(data).pause()})
            if path == "/api/resume":
                return self._send(200, {"ok": self._job(data).resume()})
            if path == "/api/browse":
                return self._send(200, {"folder": _pick_folder(data.get("folder"))})
            if path == "/api/open":
                job = self._job(data)
                target = job.output if job.output and os.path.exists(job.output) else job.folder
                if os.name == "nt":
                    if target == job.output:
                        import subprocess
                        subprocess.Popen(["explorer", "/select,", os.path.normpath(target)])
                    else:
                        os.startfile(target)  # noqa: S606
                return self._send(200, {"ok": True})
            return self._send(404, {"error": "Not found"})
        except ExtractError as e:
            return self._send(400, {"error": str(e)})
        except LookupError as e:
            return self._send(404, {"error": str(e)})
        except Exception as e:  # noqa: BLE001
            return self._send(500, {"error": str(e)})


def _free_port(preferred):
    for port in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise OSError("No free port found.")


def run(port=8765, open_browser=True, connections=8):
    _settings["connections"] = connections
    port = _free_port(port)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.daemon_threads = True
    url = f"http://localhost:{port}"
    print(f"YTDownloader UI is running at {url}")
    print("Keep this window open while downloading. Press Ctrl+C (or close the window) to stop.")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
        for job in _jobs.values():
            job.pause()
        for job in _jobs.values():
            job.wait(10)
    finally:
        httpd.server_close()
    return 0
