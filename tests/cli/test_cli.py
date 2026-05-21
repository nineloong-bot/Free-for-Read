import subprocess
import sys
import time

import httpx


def test_cli_serve_prints_ready_line_and_responds_to_health() -> None:
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "free_for_read.cli",
            "serve",
            "--port",
            "0",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        ready_line = process.stdout.readline().strip() if process.stdout else ""
        assert ready_line.startswith("READY http://127.0.0.1:"), f"Got: {ready_line}"

        port = int(ready_line.rsplit(":", 1)[-1])

        for _ in range(20):
            try:
                response = httpx.get(f"http://127.0.0.1:{port}/health", timeout=1)
                break
            except httpx.ConnectError:
                time.sleep(0.05)
        else:
            raise AssertionError("Server did not become healthy")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    finally:
        process.terminate()
        process.wait(timeout=5)


def test_cli_respects_explicit_port() -> None:
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "free_for_read.cli",
            "serve",
            "--port",
            "18765",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        ready_line = process.stdout.readline().strip() if process.stdout else ""
        assert ready_line == "READY http://127.0.0.1:18765", f"Got: {ready_line}"

        for _ in range(20):
            try:
                response = httpx.get("http://127.0.0.1:18765/health", timeout=1)
                break
            except httpx.ConnectError:
                time.sleep(0.05)
        else:
            raise AssertionError("Server did not become healthy")

        assert response.status_code == 200
    finally:
        process.terminate()
        process.wait(timeout=5)
