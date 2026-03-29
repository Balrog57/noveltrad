import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"


def iter_source_files():
    return sorted(SRC_ROOT.rglob("*.py"))


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_source(path: Path) -> ast.AST:
    return ast.parse(read_source(path), filename=str(path))


def module_target_exists(module_name: str) -> bool:
    module_path = REPO_ROOT.joinpath(*module_name.split("."))
    return module_path.with_suffix(".py").is_file() or (module_path / "__init__.py").is_file()


def get_class_methods(path: Path, class_name: str) -> set[str]:
    tree = parse_source(path)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                item.name
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
    raise AssertionError(f"Class {class_name} not found in {path}")


class StaticContractsTests(unittest.TestCase):
    def test_from_import_targets_exist(self):
        missing = []

        for path in iter_source_files():
            tree = parse_source(path)
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                if node.level != 0 or not node.module or not node.module.startswith("src."):
                    continue
                if not module_target_exists(node.module):
                    missing.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno} -> {node.module}")

        self.assertFalse(
            missing,
            "Missing import targets detected:\n" + "\n".join(missing),
        )

    def test_required_compatibility_methods_exist(self):
        mainwindow_methods = get_class_methods(SRC_ROOT / "gui" / "mainwindow.py", "MainWindow")
        editor_methods = get_class_methods(SRC_ROOT / "gui" / "controllers" / "editor_controller.py", "EditorController")
        project_manager_methods = get_class_methods(SRC_ROOT / "core" / "project_manager.py", "ProjectManager")
        sidebar_methods = get_class_methods(SRC_ROOT / "gui" / "components.py", "Sidebar")

        self.assertTrue(
            {"load_chapters", "load_segments", "load_glossary", "update_project_ui", "get_active_segment_card"} <= mainwindow_methods
        )
        self.assertTrue({"get_segment_card", "on_segment_card_clicked"} <= editor_methods)
        self.assertIn("get_chapter_segments", project_manager_methods)
        self.assertIn("set_active_item", sidebar_methods)

    def test_segment_cards_use_database_ids(self):
        source = read_source(SRC_ROOT / "gui" / "components.py")
        self.assertIn("self.segment_id = segment.id", source)

    def test_no_stale_gui_fragments_remain(self):
        banned_fragments = {
            "status_bar.showMessage(": "use statusBar().showMessage()",
            "src.gui.segment_card": "SegmentCard now lives in src.gui.components",
            "src.gui.stats_dialog": "StatisticsDialog now lives in src.gui.statistics_dialog",
            "SegmentStatus.TRANSLATED": "legacy status removed",
            "SegmentStatus.VERIFIED": "legacy status removed",
            "source_text.text()": "SegmentCard source editor is a QTextEdit",
            "* { box-sizing: border-box; }": "format() HTML templates must escape CSS braces",
        }

        offenders = []
        for path in iter_source_files():
            source = read_source(path)
            for fragment, reason in banned_fragments.items():
                if fragment in source:
                    offenders.append(f"{path.relative_to(REPO_ROOT)} -> {fragment} ({reason})")

        self.assertFalse(
            offenders,
            "Stale source fragments detected:\n" + "\n".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
