import unittest
from pathlib import Path
from types import SimpleNamespace

from src.core.tmx_handler import TMXHandler

REPO_ROOT = Path(__file__).resolve().parents[1]


class TMXHandlerTests(unittest.TestCase):
    def test_export_uses_status_value_for_enum_like_objects(self):
        segment = SimpleNamespace(
            source_text="Hello world",
            target_text="Bonjour le monde",
            status=SimpleNamespace(value="validated"),
        )

        temp_dir = REPO_ROOT / ".tmp_test_outputs"
        temp_dir.mkdir(exist_ok=True)
        output_path = temp_dir / "sample.tmx"

        try:
            TMXHandler.export_tmx_v3([segment], "en", "fr", output_path)
            content = output_path.read_text(encoding="utf-8")
        finally:
            if output_path.exists():
                output_path.unlink()
            if temp_dir.exists():
                temp_dir.rmdir()

        self.assertIn("validated", content)
        self.assertNotIn("namespace(value=", content)


if __name__ == "__main__":
    unittest.main()
