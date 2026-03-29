import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
KNOWN_STATUS_NAMES = {"UNTRANSLATED", "MACHINE", "AI_REFINED", "VALIDATED"}


class SegmentStatusContractTests(unittest.TestCase):
    def test_only_declared_segment_status_members_are_used(self):
        unknown_references = []

        for path in sorted(SRC_ROOT.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Attribute):
                    continue
                if not isinstance(node.value, ast.Name) or node.value.id != "SegmentStatus":
                    continue
                if not node.attr.isupper():
                    continue
                if node.attr not in KNOWN_STATUS_NAMES:
                    unknown_references.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno} -> {node.attr}")

        self.assertFalse(
            unknown_references,
            "Unknown SegmentStatus members referenced:\n" + "\n".join(unknown_references),
        )


if __name__ == "__main__":
    unittest.main()
