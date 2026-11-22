# YTDownloader

A small, fast YouTube downloader for Windows. You can use it from **CMD** or from a **web page on your own PC**.

Each file is downloaded over **many connections at once**, like IDM. Downloads can be **paused and resumed**, even after closing the program or restarting the PC. You can save **video** (up to 4K) or **audio** (M4A, Opus or MP3).

```
ytd -url    →  download in the console (link → type → quality → download)
ytd -ui     →  open the web UI in your browser (http://localhost:8765)
```

---

## Table of Contents

- [Features](#features)
- [Download](#download)
- [One-Click Setup](#one-click-setup)
- [Requirements](#requirements)
- [Command-Line Usage](#command-line-usage)
- [Web UI Usage](#web-ui-usage)
- [Cookies ("confirm you're not a bot")](#cookies-confirm-youre-not-a-bot)
- [Quality Options](#quality-options)
- [Pause and Resume](#pause-and-resume)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Building from Source](#building-from-source)
- [Troubleshooting](#troubleshooting)
- [Contributing and Security](#contributing-and-security)
- [Disclaimer](#disclaimer)
- [License](#license)

---

## Features

| Feature | Details |
|---|---|
| **Fast downloads** | Each stream is split into byte ranges and downloaded on several connections at once (8 by default, up to 32). When a connection finishes early, it takes over half of the largest remaining part, so every connection stays busy until the end. |
| **Video and audio together** | YouTube serves high-quality video and audio as separate streams. Both download at the same time, then ffmpeg joins them into one `.mp4` without re-encoding. |
| **Pause / Resume** | Progress is saved about once a second. You can pause from the console or the UI, or close the program, and continue later from the same point. |
| **Expired links fixed automatically** | YouTube stream links expire after a few hours. When the server refuses a link (HTTP 403/410), the program gets a new one and continues. |
| **Quality choice** | Lists the qualities the video really has (2160p60, 1440p60, 1080p60, 720p … 144p), with the estimated size of each. |
| **Audio modes** | Original M4A (AAC) or Opus with no re-encoding, or MP3 at 320, 192 or 128 kbps. |
| **Two interfaces** | An interactive console mode, and a local web UI with a detailed progress view. |
| **Single exe** | `YTDownloader.exe` with Python built in, in 64-bit (x64) and 32-bit (x86) versions. `ytd.cmd` gives it the short name `ytd`. |
| **One-click setup** | Double-click `setup.bat` to install everything, build the exe and open the documentation. |
| **Cookies support** | If YouTube asks you to confirm you're not a bot, use cookies from a `cookies.txt` file or straight from a browser. |
| **Local only** | The web UI listens on `127.0.0.1`, so other computers on your network can't reach it. |

---

## Download

### Install with winget (easiest)

```powershell
winget install JayathuShehan.YTDownloader
```

This one command installs YTDownloader together with **ffmpeg** and **Deno** (on 64-bit Windows), and adds the **`ytd`** command to your PATH. Open a **new** terminal afterwards, then `ytd -url` and `ytd -ui` work from any folder, in CMD and PowerShell.

| Task | Command |
|---|---|
| Update to the latest version | `winget upgrade JayathuShehan.YTDownloader` |
| Uninstall | `winget uninstall JayathuShehan.YTDownloader` |

### Download manually

Get the files from the [Releases](https://github.com/JayathuShehan/youtube-downloader/releases) page.

| File | Use it when |
|---|---|
| `YTDownloader-1.0.0-x64.zip` | **Recommended.** 64-bit Windows 10/11. Contains `YTDownloader.exe`, `ytd.cmd`, the docs page, README and LICENSE. |
| `YTDownloader-1.0.0-x64.exe` | 64-bit Windows, if you only want the program |
| `YTDownloader-1.0.0-x86.zip` | 32-bit Windows (see the note below) |
| `YTDownloader-1.0.0-x86.exe` | 32-bit Windows, program only |
| Source code (zip / tar.gz) | To build it yourself with [One-Click Setup](#one-click-setup) |

Not sure which you have? Open **Settings → System → About** and look at **System type**. Almost all PCs today are 64-bit.

> **32-bit Windows:** YouTube needs Deno or Node.js to solve its JavaScript check, and neither of them supports 32-bit Windows anymore. On a real 32-bit PC, YouTube downloads may fail. The x86 build works fully on 64-bit Windows.

**After downloading:**

1. Extract the zip, e.g. to `C:\Tools\YTDownloader\`. If you downloaded only the exe, rename it to `YTDownloader.exe`. To use the short name `ytd`, put `ytd.cmd` from the zip next to it.
2. Install the [requirements](#requirements): ffmpeg and Deno.
3. Open CMD in that folder and run `ytd -url` or `ytd -ui`, or double-click `YTDownloader.exe` to open the web UI.
4. Optional: add the folder to your **PATH** so `ytd` works from any folder.
   - Start → "Edit the system environment variables" → Environment Variables → `Path` → New → add the folder.

Open `docs\index.html` (included in the zip) for the full documentation in your browser.

---

## One-Click Setup

Building from source is a double-click away. Download **Source code (zip)** from the Releases page (or clone the repo), extract it, and **double-click `setup.bat`**. It does the following:

1. **Checks for Python 3.10+** and installs Python 3.12 with `winget` if it's missing (just for your user account, and added to PATH).
2. **Checks for ffmpeg** and installs it with `winget` if it's missing.
3. **Checks for Deno or Node.js** and installs Deno with `winget` if neither is found.
4. **Builds the program:** creates a virtual environment, installs the Python packages and builds `dist\YTDownloader.exe`, with `ytd.cmd` next to it.
5. **Opens the documentation** (`docs\index.html`) in your browser, and opens the `dist` folder.

On 32-bit Windows it builds the 32-bit version into `dist-x86\` instead.

> Installing with winget accepts each package's license for you. If winget is missing, install **App Installer** from the Microsoft Store, or install Python, ffmpeg and Deno yourself, then run `setup.bat` again. If something fails, the window stays open so you can read the error.

---

## Requirements

- **Windows 10 or 11** (64-bit recommended, see the 32-bit note above)
- **ffmpeg** joins video and audio and converts to MP3.
  - Put `ffmpeg.exe` in the same folder as `YTDownloader.exe`, **or**
  - install it: `winget install Gyan.FFmpeg`
- **A JavaScript runtime: Deno (recommended) or Node.js.** YouTube makes downloaders solve a JavaScript check before it serves full-speed streams. Without a runtime, downloads may fail or be missing formats.
  - `winget install DenoLand.Deno`  *(or)*  `winget install OpenJS.NodeJS`

To check that both are installed, run these in CMD:

```
ffmpeg -version
deno --version
```

- **Python 3.10+** is only needed to build from source. [One-Click Setup](#one-click-setup) installs it for you.

---

## Command-Line Usage

Open **CMD** in the folder that contains the exe (or anywhere, if the folder is on PATH):

```
ytd -url
```

The program then asks you step by step:

```
YTDownloader - fast YouTube downloader

? Enter URL: https://www.youtube.com/watch?v=aqz-KE-bpKQ
Getting video info...

Title   : Big Buck Bunny 60fps 4K - Official Blender Foundation Short Film
Channel : Blender
Length  : 10:35

? Select type
   [1] Video
   [2] Audio
? Enter number [1]: 1

? Select quality
   [1] Best available (2160p60)
   [2] 2160p60  (VP9, ~1.3 GB)
   [3] 1440p60  (VP9, ~480.8 MB)
   [4] 1080p60  (H.264, ~275.0 MB)
   [5] 720p60  (H.264, ~172.9 MB)
   ...
? Enter number [1]: 4

? Save to (Enter = current folder) [C:\Users\you\Videos]:

Title : Big Buck Bunny 60fps 4K - Official Blender Foundation Short Film
Stage : Downloading video + audio (1080p60)    Connections: 16
[██████████████░░░░░░░░░░░░░░░░]  47.3%  130.1 / 275.0 MB  9.2 MB/s  ETA 00:15
Keys: [P] pause  [R] resume  [Q] quit (progress is saved, run again to resume)

✔ Saved: C:\Users\you\Videos\Big Buck Bunny 60fps 4K - Official Blender Foundation Short Film.mp4
```

### Keys during a download

| Key | Action |
|---|---|
| `P` | Pause |
| `R` | Resume |
| `Q` or `Ctrl+C` | Save progress and quit. Run the same command again to continue. |

### All options

```
ytd [-url [LINK] | -ui] [-o FOLDER] [-c N] [--cookies FILE | --cookies-from-browser BROWSER]
    [--port PORT] [--no-browser] [-v] [-h]
```

| Option | Description |
|---|---|
| `-url` | Interactive console download. Asks for the link. |
| `-url LINK` | Same as above, but skips the link question. |
| `-ui` | Starts the web UI and opens it in your default browser. |
| *(no options)* | Same as `-ui`. This is also what happens when you double-click the exe. |
| `-o FOLDER`, `--output FOLDER` | Folder to save into (console mode). |
| `-c N`, `--connections N` | Connections per stream, from 1 to 32. Default is 8. |
| `--cookies FILE` | Uses cookies from a `cookies.txt` file. See [Cookies](#cookies-confirm-youre-not-a-bot). |
| `--cookies-from-browser BROWSER` | Uses cookies from a browser: `firefox`, `chrome`, `edge`, `brave`, `opera` or `vivaldi`. Add `:PROFILE` for a specific profile. |
| `--port PORT` | Port for the web UI. Default is 8765. If it's taken, the next free port is used. |
| `--no-browser` | Starts the web UI server without opening a browser. |
| `-v`, `--version` | Shows the version. |
| `-h`, `--help` | Shows help. |

Single-dash and double-dash forms both work (`-url` / `--url`, `-ui` / `--ui`).

### Examples

```
ytd -url
ytd -url https://youtu.be/aqz-KE-bpKQ
ytd -url https://youtu.be/aqz-KE-bpKQ -o D:\Videos
ytd -url https://youtu.be/aqz-KE-bpKQ -c 16
ytd -url https://youtu.be/aqz-KE-bpKQ --cookies C:\Users\you\cookies.txt
ytd -url --cookies-from-browser firefox
ytd -ui
ytd -ui --port 9000
```

> **PowerShell users:** PowerShell doesn't run programs from the current folder by name. Type `.\ytd -url` instead, or add the folder to PATH.

---

## Web UI Usage

```
ytd -ui
```

Your browser opens **http://localhost:8765**. Keep the console window open while downloading. Closing it stops the downloads, but their progress is saved.

1. **Video link**: paste a link. The info loads automatically, or press **Fetch**. You'll see the thumbnail, title, channel and length.
2. **Type**: choose **Video** or **Audio**.
3. **Quality**: pick from the list. Each option shows its codec and estimated size.
4. **Save to**: type a folder, or click **Browse…** to open the Windows folder picker. The default is your `Downloads` folder, and the last folder you used is remembered.
5. **Cookies**: leave this on **None** unless YouTube asks you to confirm you're not a bot. Then pick a browser, or **From a cookies.txt file…** and choose the file. See [Cookies](#cookies-confirm-youre-not-a-bot).
6. **Connections**: 1, 4, 8, 16, 24 or 32 per stream.
7. **Start**, **Pause**, **Resume**. After an error, Resume changes to **Retry**.

### Progress panel

- Overall progress bar and percentage
- Current stage: getting info, downloading, merging, converting, completed
- Downloaded / total size, speed, time left, active connections, quality
- **A bar for each stream** (video and audio) showing every connection's segment filling up live, like IDM
- **Show in folder** when finished, which opens Explorer with the file selected

If you start more than one download, a **Downloads this session** list appears. Click an item to view its progress.

---

## Cookies ("confirm you're not a bot")

Sometimes YouTube refuses to give video details and shows this error:

> Sign in to confirm you're not a bot.

YouTube decides this based on your IP address. It happens more often after many downloads in a short time, on a VPN or proxy, or on shared networks. Waiting a few hours or switching networks often clears it. The reliable fix is to give YTDownloader the cookies of a browser where you are **signed in to YouTube**. YouTube then treats the requests as coming from you.

**Option 1: a cookies.txt file (works with every browser)**

1. In your browser, sign in to YouTube.
2. Install an extension that exports cookies in the Netscape `cookies.txt` format, for example **Get cookies.txt LOCALLY** (Chrome/Edge) or **cookies.txt** (Firefox).
3. Open youtube.com, click the extension, and export the cookies for that site to a file.
4. Use the file:
   - Web UI: **Cookies → From a cookies.txt file…**, then **Browse…** to the file.
   - CLI: `ytd -url --cookies C:\path\to\cookies.txt`

Cookies expire after a while. If the error comes back, export a fresh file.

**Option 2: read cookies straight from a browser**

- Web UI: **Cookies → From Firefox** (or another browser).
- CLI: `ytd -url --cookies-from-browser firefox`

This works best with **Firefox**. Chrome, Edge and other Chromium browsers lock their cookie database while open and encrypt it, so reading from them often fails. Use Option 1 for those.

> **Keep your cookies private.** A cookies file lets anyone use your YouTube account. Don't share it or commit it to a repository. YTDownloader only sends the cookies to YouTube.

The web UI remembers your choice. `--cookies` and `--cookies-from-browser` also work with `-ui` and set the default there.

---

## Quality Options

### Video

| Option | Notes |
|---|---|
| Best available | The highest resolution and frame rate the video has |
| 2160p / 1440p | 4K / 2K. YouTube only offers these as VP9 or AV1. |
| 1080p / 720p / 480p / 360p / 240p / 144p | H.264 is used when available, because it plays everywhere |
| `60` suffix (e.g. `1080p60`) | 60 fps version |

Video is saved as **`.mp4`**: the chosen video stream plus the best AAC audio, joined without re-encoding. In the rare case a codec combination doesn't fit in MP4, the file is saved as **`.mkv`** instead.

### Audio

| Option | Output | Notes |
|---|---|---|
| Best original (M4A / AAC) | `.m4a` | Not re-encoded, so no quality loss |
| Best original (Opus) | `.opus` | Not re-encoded. Often a smaller file. |
| MP3 320 / 192 / 128 kbps | `.mp3` | Converted with ffmpeg (stereo) |

---

## Pause and Resume

While downloading, the program keeps two files in the save folder:

```
<Title> [<video id>].f<format>.part             ← the partly downloaded data
<Title> [<video id>].f<format>.part.ytd.json    ← which bytes are already done
```

- **Pause** (button, `P`, `Q` or `Ctrl+C`) stops all connections and saves the progress file.
- **Resume** continues from the saved byte positions.
- **After closing the program or a crash:** run the same link with the **same quality** and **same folder**. The program finds the files and continues.
- When the download finishes and the file is saved, both temporary files are deleted.

To give up on a paused download, just delete its `.part` and `.part.ytd.json` files.

---

## How It Works

```
             ┌──────────────┐  stream links  ┌──────────────────────────────┐
  link ───►  │    yt-dlp    │ ─────────────► │ segmented downloader         │
             │ (extractor)  │                │  video: N parallel ranges ─┐ │
             └──────────────┘                │  audio: N parallel ranges ─┤ │
                    ▲  new link              └────────────────────────────┼─┘
                    └── when a link expires (HTTP 403/410)                ▼
                                                     ffmpeg: join / convert ──► final file
```

1. **Getting the streams**: [yt-dlp](https://github.com/yt-dlp/yt-dlp) is used as a library, only to read the video info and find the direct stream links. It also handles YouTube's signature and JavaScript checks, using Deno or Node.
2. **Segmented downloading** (`ytd/segdl.py`):
   - A tiny `Range: bytes=0-0` request finds the file size and checks that the server supports byte ranges.
   - The file is created at full size, then split into N segments.
   - Each connection downloads its segment in requests of up to 10 MB. YouTube slows down very long single requests, so this avoids that.
   - **Dynamic splitting:** when a connection finishes, it splits the largest remaining segment in half and takes the second half.
   - Every connection writes straight to its own position in the file.
   - Speed is averaged over the last 3 seconds.
3. **Video and audio at the same time**: both streams have their own set of connections, so with 8 connections per stream, up to 16 run together.
4. **Joining / converting** (`ytd/ffmpeg.py`): `ffmpeg -c copy` joins the streams without re-encoding, and audio is re-encoded only for MP3. ffmpeg's progress output drives the "processing" bar.
5. **Errors**: each connection retries with increasing waits. An expired link triggers a single refresh shared by all connections.

Why is it faster? YouTube limits the speed of each connection. Using many connections at once gets much closer to your full internet speed. In testing on one connection, 1 connection reached ~5.4 MB/s and 16 connections reached ~9 MB/s, which was the full speed of that line.

---

## Project Structure

```
youtube-downloader/
├─ ytd/
│  ├─ __init__.py      version / app name
│  ├─ __main__.py      command-line options (-url, -ui, ...)
│  ├─ extractor.py     yt-dlp wrapper: video info, quality list, stream selection, link refresh
│  ├─ segdl.py         multi-connection segmented downloader with pause/resume
│  ├─ job.py           one download: streams in parallel → join/convert → final file
│  ├─ ffmpeg.py        finds ffmpeg; join, remux and MP3 conversion with progress
│  ├─ cli.py           interactive console mode and live progress bar
│  ├─ server.py        local web server and JSON API for the web UI
│  ├─ util.py          shared helpers (sizes, times, safe file names, paths)
│  └─ web/
│     ├─ index.html    web UI page
│     ├─ style.css     styles (light and dark theme)
│     └─ app.js        UI logic: fetch, start/pause/resume, live progress
├─ docs/
│  └─ index.html       full documentation page (opens in any browser, works offline)
├─ setup.bat           one-click setup: double-click to install, build and open the docs
├─ setup.ps1           what setup.bat runs
├─ build.ps1           build script (PyInstaller, x64 or x86)
├─ run_ytd.py          entry script used to build the exe
├─ ytd.cmd             "ytd" shortcut for YTDownloader.exe
├─ requirements.txt    Python dependencies
├─ LICENSE
└─ README.md
```

### Web UI API

The web server only accepts requests from `localhost`, and POST requests must send JSON.

`cookies` is `{"browser": "firefox"}`, `{"file": "C:\\path\\cookies.txt"}` or `null`.

| Method | Path | Body / query | Returns |
|---|---|---|---|
| `POST` | `/api/info` | `{url, cookies?}` | title, thumbnail, channel, length, video and audio quality lists |
| `POST` | `/api/start` | `{url, type, quality, folder, connections, cookies?}` | `{job_id}` |
| `POST` | `/api/pause` | `{job_id}` | `{ok}` |
| `POST` | `/api/resume` | `{job_id}` | `{ok}` |
| `GET` | `/api/status?job_id=` | | progress snapshot (state, stage, bytes, speed, ETA, segments for each stream) |
| `GET` | `/api/jobs` | | all downloads in this session |
| `GET` | `/api/config` | | default folder, connections, cookies, version |
| `POST` | `/api/browse` | `{folder}` | opens the Windows folder picker and returns `{folder}` |
| `POST` | `/api/browse_file` | `{file}` | opens the Windows file picker for a cookies file and returns `{file}` |
| `POST` | `/api/open` | `{job_id}` | shows the finished file in Explorer |

---

## Building from Source

The easiest way is [One-Click Setup](#one-click-setup) (double-click `setup.bat`). To do it by hand, you need **Python 3.10 or newer** on Windows.

```powershell
git clone https://github.com/JayathuShehan/youtube-downloader.git
cd youtube-downloader
powershell -ExecutionPolicy Bypass -File build.ps1
```

| Command | Result |
|---|---|
| `build.ps1` | 64-bit build → `dist\YTDownloader.exe` |
| `build.ps1 -Arch x86` | 32-bit build → `dist-x86\YTDownloader.exe` (needs a 32-bit Python) |
| `build.ps1 -Python C:\path\python.exe` | Uses a specific Python |

`build.ps1` does the following:

1. finds a suitable Python (64-bit or 32-bit) and creates a virtual environment: `.venv`, or `.venv-x86` for 32-bit
2. installs `requirements.txt` and PyInstaller
3. builds a single-file `YTDownloader.exe`, including the web UI files and yt-dlp's JavaScript challenge solver
4. copies `ytd.cmd` next to the exe

**32-bit Python:** use the python.org "Windows installer (32-bit)", or run `uv python install cpython-3.12-windows-x86-none`.

### Run without building

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run_ytd.py -url
.venv\Scripts\python run_ytd.py -ui
```

### Dependencies

| Package | Used for |
|---|---|
| `yt-dlp` | video info and stream links |
| `yt-dlp-ejs` | YouTube JavaScript challenge solver scripts (run with Deno or Node) |
| `requests` | HTTP connections for the segmented downloader |
| `pyinstaller` | building the exe (build only) |

### Keeping YouTube support up to date

YouTube changes often. If downloads stop working, update yt-dlp and rebuild:

```powershell
.venv\Scripts\python -m pip install -U yt-dlp yt-dlp-ejs
powershell -ExecutionPolicy Bypass -File build.ps1
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `'ytd' is not recognized...` | Run it from the folder that has `ytd.cmd` and `YTDownloader.exe`, or add that folder to PATH. In PowerShell, use `.\ytd`. |
| `ffmpeg was not found` | Put `ffmpeg.exe` next to `YTDownloader.exe`, or run `winget install Gyan.FFmpeg` and open a new CMD window. |
| Formats missing, or download fails right away | Install Deno (`winget install DenoLand.Deno`) or Node.js, then update yt-dlp (see above). |
| `Sign in to confirm you're not a bot` | Use cookies from a browser where you are signed in to YouTube. See [Cookies](#cookies-confirm-youre-not-a-bot). |
| `Could not read cookies from Chrome` (or Edge) | Chromium browsers lock and encrypt their cookies. Export a `cookies.txt` file instead, or use Firefox. |
| `YouTube keeps refusing the stream (HTTP 403)` | Use fewer connections (`-c 4`), wait a little, and try again. |
| Private, age-restricted or members-only video | These need a signed-in account. They may work with [cookies](#cookies-confirm-youre-not-a-bot) from an account that can watch them. |
| Playlist link | Only single videos are supported. A link with `&list=` downloads just that video. |
| Web UI doesn't open | Open `http://localhost:8765` yourself. If that port is busy, the console shows the port being used. |
| Download is slow | Try 16 connections. Also check your own internet speed, which is the upper limit. |
| Windows SmartScreen warning | The exe isn't code-signed. Click **More info → Run anyway**, or build it yourself. |
| `setup.bat` says winget is missing | Install **App Installer** from the Microsoft Store, or install Python, ffmpeg and Deno yourself. |
| Setup installed something but can't find it | Close the window and run `setup.bat` again, so it picks up the updated PATH. |

---

## Contributing and Security

- **Bugs and ideas:** open an issue with the **Bug report** or **Feature request** form.
- **Pull requests:** read [CONTRIBUTING.md](CONTRIBUTING.md). `main` is protected, so every change goes through a reviewed pull request.
- **Security problems:** report them privately as described in [SECURITY.md](SECURITY.md), not in a public issue.
- **Behaviour:** everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
- **Downloads:** get YTDownloader only from this repository's [Releases](https://github.com/JayathuShehan/youtube-downloader/releases) page.

---

## Disclaimer

This tool is for personal use. Only download videos you own or have permission to download, and follow [YouTube's Terms of Service](https://www.youtube.com/t/terms) and your local copyright laws. The author is not responsible for how it is used.

---

## License

[MIT](LICENSE) © 2026 Jayathu Shehan Dewmina
