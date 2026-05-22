import argparse
import secrets
import socket
import sys
from pathlib import Path

import uvicorn

from free_for_read.api.app import create_app


def _serve(host: str, port: int, storage_root: str, shutdown_token: str | None = None) -> None:
    token = shutdown_token or secrets.token_urlsafe(24)
    app = create_app(storage_root=Path(storage_root), shutdown_token=token)
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=host,
            port=port,
            log_config=None,
        )
    )

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen(socket.SOMAXCONN)
        actual_port = sock.getsockname()[1]
        print(f"READY http://{host}:{actual_port} shutdown_token={token}", flush=True)
        server.run(sockets=[sock])


def main() -> None:
    parser = argparse.ArgumentParser(prog="free-for-read")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    serve_parser.add_argument("--port", type=int, default=0, help="Port to bind (0=ephemeral)")
    serve_parser.add_argument("--storage", default="storage", help="Storage root directory")
    serve_parser.add_argument("--shutdown-token", default=None, help=argparse.SUPPRESS)

    args = parser.parse_args()

    if args.command == "serve":
        _serve(args.host, args.port, args.storage, args.shutdown_token)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
