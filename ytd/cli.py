"""Interactive command-line mode: ytd -url"""

import os
import sys
import time

from . import extractor
from .extractor import ExtractError
from .job import Job
from .util import fmt_bytes, fmt_duration, fmt_eta

try:
    import msvcrt  # Windows: non-blocking key reads
except ImportError:  # pragma: no cover
    msvcrt = None

CYAN, GREEN, YELLOW, RED, DIM, BOLD, RESET = (
    "\x1b[36m", "\x1b[32m", "\x1b[33m", "\x1b[31m", "\x1b[2m", "\x1b[1m", "\x1b[0m")


def _enable_ansi():
    if os.name == "nt":
        os.system("")  # turns on VT escape codes in the Windows console
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def _ask(prompt, default=None):
    suffix = f" {DIM}[{default}]{RESET}" if default else ""
    try:
        value = input(f"{CYAN}?{RESET} {prompt}{suffix}: ").strip().strip('"')
    except EOFError:
        value = ""
    return value or (default or "")


def _choose(prompt, options):
    """options: list of (id, label). Returns the chosen id."""
    print(f"{CYAN}?{RESET} {prompt}")
    for i, (_, label) in enumerate(options, 1):
        print(f"   {BOLD}[{i}]{RESET} {label}")
    while True:
        raw = _ask("Enter number", "1")
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        print(f"   {RED}Please enter a number from 1 to {len(options)}.{RESET}")


def _bar(fraction, width=30):
    fraction = max(0.0, min(1.0, fraction))
    filled = int(round(fraction * width))
    return "█" * filled + "░" * (width - filled)


def _render(job, lines_before):
    s = job.snapshot()
    if s["state"] == "processing":
        frac = s["process_progress"] / 100
        stats = f"{s['process_progress']:5.1f}%"
    else:
        frac = s["percent"] / 100
        stats = (f"{s['percent']:5.1f}%  {fmt_bytes(s['downloaded'])} / {fmt_bytes(s['total'])}  "
                 f"{fmt_bytes(s['speed'])}/s  ETA {fmt_eta(s['eta'])}")
    color = YELLOW if s["state"] == "paused" else GREEN
    out = [
        f"Stage : {s['stage']}    {DIM}Connections: {s['connections']}{RESET}",
        f"{color}[{_bar(frac)}]{RESET}  {stats}",
        f"{DIM}Keys: [P] pause  [R] resume  [Q] quit (progress is saved, run again to resume){RESET}",
    ]
    if lines_before:
        sys.stdout.write(f"\x1b[{lines_before}F")
    for line in out:
        sys.stdout.write("\x1b[2K" + line + "\n")
    sys.stdout.flush()
    return len(out)


def _read_key():
    if msvcrt and msvcrt.kbhit():
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):  # arrow/function keys send two codes
            msvcrt.getwch()
            return None
        return ch.lower()
    return None


def run(url=None, folder=None, connections=8, cookies=None):
    _enable_ansi()
    print(f"{BOLD}YTDownloader{RESET} {DIM}- fast YouTube downloader{RESET}\n")
    if cookies:
        print(f"{DIM}Using cookies from {cookies.get('browser') or cookies.get('file')}{RESET}\n")

    while True:
        if not url:
            url = _ask("Enter URL")
        if not url:
            print(f"{RED}No URL given.{RESET}")
            return 1
        print(f"{DIM}Getting video info...{RESET}")
        try:
            info = extractor.fetch_info(url, cookies)
            opts = extractor.build_options(info)
            break
        except ExtractError as e:
            print(f"{RED}Error: {e}{RESET}\n")
            url = None

    print(f"\n{BOLD}Title   :{RESET} {opts['title']}")
    if opts["uploader"]:
        print(f"{BOLD}Channel :{RESET} {opts['uploader']}")
    if opts["duration"]:
        print(f"{BOLD}Length  :{RESET} {fmt_duration(opts['duration'])}")
    print()

    kinds = []
    if opts["video"]:
        kinds.append(("video", "Video"))
    if opts["audio"]:
        kinds.append(("audio", "Audio"))
    if not kinds:
        print(f"{RED}No downloadable streams found.{RESET}")
        return 1
    kind = _choose("Select type", kinds)
    print()
    quality = _choose("Select quality", [(q["id"], q["label"]) for q in opts[kind]])
    print()
    if not folder:
        folder = _ask("Save to (Enter = current folder)", os.getcwd())
    print()

    job = Job(url, kind, quality, folder, connections, info=info, cookies=cookies)
    job.start()
    lines = 0
    print(f"{BOLD}Title :{RESET} {opts['title']}")
    try:
        while True:
            lines = _render(job, lines)
            if job.state in ("done", "error") and not job.alive:
                break
            if job.state == "paused" and not job.alive and getattr(job, "_quit", False):
                break
            key = _read_key()
            if key == "p":
                job.pause()
            elif key == "r":
                job.resume()
            elif key == "q" and job.state != "processing":  # never interrupt merging
                job._quit = True
                if job.state == "paused" or not job.pause():
                    break
            time.sleep(0.25)
    except KeyboardInterrupt:
        job._quit = True
        job.pause()
        job.wait(15)
        _render(job, lines)

    if job.state == "done":
        print(f"\n{GREEN}✔ Saved:{RESET} {job.output}")
        return 0
    if job.state == "error":
        print(f"\n{RED}✖ {job.error}{RESET}")
        return 1
    print(f"\n{YELLOW}Paused. Run the same command with the same quality to resume.{RESET}")
    return 2
