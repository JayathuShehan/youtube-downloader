# Contributing to YTDownloader

Thanks for helping! Bug reports, ideas and pull requests are all welcome. Please read the [Code of Conduct](CODE_OF_CONDUCT.md) first.

## Reporting a Bug

1. First update to the [latest release](https://github.com/JayathuShehan/youtube-downloader/releases). Many YouTube problems are fixed by a newer yt-dlp.
2. Search the [existing issues](https://github.com/JayathuShehan/youtube-downloader/issues) to see if it's already reported.
3. Open a new issue with the **Bug report** form, and include:
   - your Windows version and which file you use (x64/x86, exe or zip)
   - the command you ran (`ytd -url`, `ytd -ui`, ...) and the video link
   - the full error message
   - `ffmpeg -version` and `deno --version` output

**Security problems:** don't open a public issue. See [SECURITY.md](SECURITY.md).

## Suggesting a Feature

Open an issue with the **Feature request** form. Explain what you want to do and why. For big changes, please wait for a reply before you start coding, so your work isn't wasted.

## Pull Requests

1. **Fork** the repository and create a branch from `main`:
   ```powershell
   git checkout -b fix/short-description
   ```
2. Set up and build:
   ```powershell
   powershell -ExecutionPolicy Bypass -File build.ps1
   ```
   Or run without building: `.venv\Scripts\python run_ytd.py -url`
3. Make your change. Keep each pull request focused on **one** fix or feature.
4. Test it:
   - `ytd -url` downloads a video, and an audio file as MP3
   - `ytd -ui` works: fetch, start, pause, resume
   - pause, then close and run again: the download continues
5. Commit with a clear message that says what changed, e.g. `Fix crash when video title has emoji`.
6. Push to your fork and open a pull request to `main`. Fill in the checklist.

Every pull request is reviewed by the maintainer before merging. `main` is protected: changes only go in through reviewed pull requests.

## Code Style

- Python 3.10+, standard library first, no new dependencies without a good reason
- Follow the style of the code around your change: clear names, short functions, comments that explain *why*
- Don't commit build output (`build/`, `dist/`, `.venv/`) or downloaded videos

## Project Layout

See [Project Structure](README.md#project-structure) in the README for what each file does.

## Legal

By contributing, you agree that your contribution is released under the [MIT License](LICENSE). Please don't add features whose main purpose is getting around DRM or paywalls, such as members-only or rented videos.
