import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class HeadlessClientSmokeTests(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get("NOVELTRAD_RUN_SLOW_SMOKE") == "1",
        "set NOVELTRAD_RUN_SLOW_SMOKE=1 to run headless subprocess smoke",
    )
    def test_headless_client_against_backend_subprocess(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "sample.txt"
            source.write_text(
                "Chapter 1\n\nThis is a short headless translation test.",
                encoding="utf-8",
            )
            port = _free_port()
            env = os.environ.copy()
            env["NOVELTRAD_TRANSLATION_TEST_MODE"] = "1"
            env["NOVELTRAD_FAKE_LLM"] = "1"
            env["NOVELTRAD_ALLOW_IDENTITY_TRANSLATION"] = "1"
            env["PYTHONPATH"] = str(root)
            backend = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "src.backend.server",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--db-path",
                    str(tmp_path / ".state.db"),
                    "--vectors",
                    str(tmp_path / ".vectors"),
                    "--log-level",
                    "WARNING",
                ],
                cwd=str(root),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                time.sleep(1.0)
                result = subprocess.run(
                    [
                        sys.executable,
                        str(root / "examples" / "headless_client.py"),
                        str(source),
                        "--base-url",
                        f"http://127.0.0.1:{port}",
                        "--profile",
                        "eco",
                        "--format",
                        "txt",
                        "--timeout",
                        "60",
                    ],
                    cwd=str(root),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=75,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
                )
                output_lines = [
                    line for line in result.stdout.splitlines() if "] output:" in line
                ]
                self.assertTrue(output_lines, result.stdout)
                output_path = Path(output_lines[-1].split("] output:", 1)[1].strip())
                self.assertTrue(output_path.exists(), output_path)
            finally:
                backend.terminate()
                try:
                    backend.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    backend.kill()
                    backend.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
