"""Entry point.

    ytd                 open the browser UI
    ytd -ui             open the browser UI
    ytd -url [link]     interactive download in the console
"""

import argparse
import sys

from ytd import APP_NAME, __version__


def build_parser():
    p = argparse.ArgumentParser(
        prog="ytd",
        description=f"{APP_NAME} {__version__} - fast multi-connection YouTube downloader",
        allow_abbrev=False,
        epilog="Examples:\n  ytd -url\n  ytd -url https://youtu.be/xxxx -o D:\\Videos\n  ytd -ui",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("-url", "--url", nargs="?", const="", metavar="LINK",
                      help="download in the console (asks for the link if not given)")
    mode.add_argument("-ui", "--ui", action="store_true", help="open the web UI in your browser (default)")
    p.add_argument("-o", "--output", metavar="FOLDER", help="download folder")
    p.add_argument("-c", "--connections", type=int, default=8, metavar="N",
                   help="connections per stream, 1-32 (default 8)")
    p.add_argument("--port", type=int, default=8765, help="port for the web UI (default 8765)")
    p.add_argument("--no-browser", action="store_true", help="start the UI server without opening a browser")
    p.add_argument("-v", "--version", action="version", version=f"{APP_NAME} {__version__}")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    conns = max(1, min(32, args.connections))
    try:
        if args.url is not None:
            from ytd import cli
            return cli.run(args.url or None, args.output, conns)
        from ytd import server
        return server.run(args.port, not args.no_browser, conns)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
