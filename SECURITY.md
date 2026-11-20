# Security Policy

## Supported Versions

Only the latest release gets security fixes.

| Version | Supported |
|---|---|
| 1.0.x (latest) | ✅ |
| older | ❌ |

## Reporting a Vulnerability

**Please don't report security problems in public issues.**

Report them privately through GitHub instead:

1. Go to the [Security tab](https://github.com/JayathuShehan/youtube-downloader/security) of this repository.
2. Click **Report a vulnerability**.
3. Describe the problem, how to reproduce it, and what an attacker could do with it.

You can expect:

- a reply within **7 days**
- updates while the fix is being worked on
- credit in the release notes once it's fixed, if you'd like it

## What Counts as a Security Issue

Examples of things to report privately:

- the local web UI (`ytd -ui`) being reachable or controllable from another website or another computer
- a crafted video link or video title that makes the program run commands, or write files outside the chosen folder
- release files (`.exe` / `.zip`) that don't match what this repository builds

Problems with YouTube itself, or videos that won't download, are normal bugs. Please report those with the **Bug report** form in [Issues](https://github.com/JayathuShehan/youtube-downloader/issues).

## Verifying Downloads

Only download YTDownloader from the [Releases page](https://github.com/JayathuShehan/youtube-downloader/releases) of this repository. Copies from anywhere else may be modified. If you're unsure, build it yourself from the source with `setup.bat`.
