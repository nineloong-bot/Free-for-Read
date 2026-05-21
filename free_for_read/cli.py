import argparse
import socket
import sys
from pathlib import Path

import uvicorn

from free_for_read.api.app import create_app


def _serve(host: str, port: int, storage_root: str) -> None:
    if port == 0:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, 0))
            port = s.getsockname()[1]

    app = create_app(storage_root=Path(storage_root))

    print(f"READY http://{host}:{port}", flush=True)

    uvicorn.run(app, host=host, port=port, log_config=None)


def main() -> None:
    parser = argparse.ArgumentParser(prog="free-for-read")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    serve_parser.add_argument("--port", type=int, default=0, help="Port to bind (0=ephemeral)")
    serve_parser.add_argument("--storage", default="storage", help="Storage root directory")

    args = parser.parse_args()

    if args.command == "serve":
        _serve(args.host, args.port, args.storage)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
