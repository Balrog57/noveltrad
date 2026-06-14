"""Tests for the multi-file FileCloud widget and the state_store
source_file plumbing.

Covers:
  * FileCloud emits a list of paths (not a single path) on drop/browse.
  * Dropping the same file twice dedupes.
  * FileCloud uses QFileDialog.getOpenFileNames (multi-select) for browse.
  * StateStore.add_chunk + list_chunks(source_file=...) round-trips.
  * Assembler groups chunks by source_file and writes one output per group.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class FileCloudMultiFileTests(unittest.TestCase):
    def _make_cloud(self):
        from PyQt6.QtWidgets import QApplication

        self._app = QApplication.instance() or QApplication([])
        from src.gui.widgets.file_cloud import FileCloud

        cloud = FileCloud()
        self.addCleanup(cloud.deleteLater)
        return cloud

    def test_drop_multiple_files_emits_list(self) -> None:
        cloud = self._make_cloud()
        captured: list[list[str]] = []
        cloud.filesSelected.connect(lambda paths: captured.append(list(paths)))
        paths = [
            str(Path("C:/tmp/a.txt")),
            str(Path("C:/tmp/b.txt")),
            str(Path("C:/tmp/c.txt")),
        ]
        cloud.add_paths(paths)
        self.assertEqual(captured[-1], paths)
        self.assertEqual(cloud.selected_paths(), paths)

    def test_drop_duplicates_are_deduplicated(self) -> None:
        cloud = self._make_cloud()
        a = str(Path("C:/tmp/a.txt"))
        b = str(Path("C:/tmp/b.txt"))
        cloud.add_paths([a])
        cloud.add_paths([a, a, b])
        self.assertEqual(cloud.selected_paths(), [a, b])

    def test_getOpenFileNames_called(self) -> None:
        cloud = self._make_cloud()
        from PyQt6.QtWidgets import QFileDialog

        with mock.patch.object(
            QFileDialog, "getOpenFileNames", return_value=(["C:/tmp/x.txt"], "")
        ) as mocked:
            cloud._open_dialog()
        mocked.assert_called_once()
        x = str(Path("C:/tmp/x.txt"))
        self.assertIn(x, cloud.selected_paths())

    def test_remove_path(self) -> None:
        cloud = self._make_cloud()
        a = str(Path("C:/tmp/a.txt"))
        b = str(Path("C:/tmp/b.txt"))
        cloud.add_paths([a, b])
        cloud.remove_path(a)
        self.assertEqual(cloud.selected_paths(), [b])

    def test_clear_removes_all_paths_and_emits_empty_list(self) -> None:
        cloud = self._make_cloud()
        captured: list[list[str]] = []
        cloud.filesSelected.connect(lambda paths: captured.append(list(paths)))
        paths = [
            str(Path("C:/tmp/a.txt")),
            str(Path("C:/tmp/b.txt")),
        ]
        cloud.add_paths(paths)
        cloud.clear()
        self.assertEqual(cloud.selected_paths(), [])
        self.assertEqual(captured[-1], [])


class StateStoreSourceFileTests(unittest.TestCase):
    def setUp(self) -> None:
        from src.backend.orchestrator.state_store import StateStore

        self._tmp = tempfile.TemporaryDirectory()
        self.store = StateStore(
            db_path=Path(self._tmp.name) / ".state.db",
            vector_dir=None,
        )

    def tearDown(self) -> None:
        self.store.close()
        self._tmp.cleanup()

    def test_chunks_tagged_with_source_file(self) -> None:
        for i in range(3):
            self.store.add_chunk(
                {
                    "id": f"c-{i}",
                    "chapter_id": "ch1",
                    "chapter_title": "Chapter 1",
                    "chunk_index": i,
                    "source_text": f"hello {i}",
                    "source_file": "C:/tmp/book1.txt",
                }
            )
        for i in range(2):
            self.store.add_chunk(
                {
                    "id": "d-" + str(i),
                    "chapter_id": "ch1",
                    "chapter_title": "Chapter 1",
                    "chunk_index": i,
                    "source_text": f"world {i}",
                    "source_file": "C:/tmp/book2.txt",
                }
            )
        only_book1 = self.store.list_chunks(source_file="C:/tmp/book1.txt")
        self.assertEqual([c["id"] for c in only_book1], ["c-0", "c-1", "c-2"])
        only_book2 = self.store.list_chunks(source_file="C:/tmp/book2.txt")
        self.assertEqual([c["id"] for c in only_book2], ["d-0", "d-1"])
        # Default value "" is allowed (legacy single-file flow).
        self.store.add_chunk(
            {
                "id": "legacy",
                "chapter_id": "ch1",
                "chapter_title": "Chapter 1",
                "chunk_index": 99,
                "source_text": "no source",
            }
        )
        self.assertEqual(
            [c["id"] for c in self.store.list_chunks(source_file="")],
            ["legacy"],
        )

    def test_legacy_db_without_source_file_is_migrated(self) -> None:
        """A DB created by NovelTrad 4.0.0 (no `source_file` column)
        must be transparently upgraded: a fresh chunk can be added and
        read back with `source_file=""` (the DEFAULT)."""
        import sqlite3

        legacy_path = Path(self._tmp.name) / ".legacy.db"
        conn = sqlite3.connect(str(legacy_path))
        # Schema mirrors pre-4.0.1 — no source_file column.
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY, chapter_id TEXT NOT NULL,
                chapter_title TEXT, chunk_index INTEGER NOT NULL,
                source_text TEXT NOT NULL, source_hash TEXT,
                glossary_version TEXT, output_hash TEXT,
                raw_translation TEXT, glossary_applied TEXT,
                qa_checked TEXT, grammar_checked TEXT,
                polished_translation TEXT, status TEXT DEFAULT 'parsed',
                error_message TEXT, metadata_json TEXT
            );
            """
        )
        # Pre-seed a legacy row to confirm we don't drop data.
        conn.execute(
            "INSERT INTO chunks (id, chapter_id, chapter_title, "
            "chunk_index, source_text) VALUES (?, ?, ?, ?, ?)",
            ("legacy-pre", "ch-old", "Old", 0, "old text"),
        )
        conn.commit()
        conn.close()

        from src.backend.orchestrator.state_store import StateStore

        store = StateStore(db_path=legacy_path, vector_dir=None)
        try:
            # The pre-existing row should still be there.
            row = store.get_chunk("legacy-pre")
            self.assertIsNotNone(row)
            self.assertEqual(row["source_text"], "old text")
            self.assertEqual(row["source_file"], "")
            # New rows can be added and the source_file column is
            # populated correctly.
            store.add_chunk(
                {
                    "id": "new",
                    "chapter_id": "ch-new",
                    "chapter_title": "New",
                    "chunk_index": 0,
                    "source_text": "new",
                    "source_file": "C:/fresh.txt",
                }
            )
            self.assertEqual(
                store.get_chunk("new")["source_file"], "C:/fresh.txt"
            )
        finally:
            store.close()


class AssemblerMultiFileTests(unittest.TestCase):
    def test_writes_one_output_per_source_file(self) -> None:
        from src.backend.agents.assembler import _grouped_by_source, _derive_output_path

        chunks = [
            {
                "id": "a-0",
                "chapter_id": "ch1",
                "chapter_title": "Chapter 1",
                "chunk_index": 0,
                "source_text": "src",
                "polished_translation": "Bonjour",
                "source_file": "C:/book1.txt",
            },
            {
                "id": "b-0",
                "chapter_id": "ch1",
                "chapter_title": "Chapter 1",
                "chunk_index": 0,
                "source_text": "src",
                "polished_translation": "Salut",
                "source_file": "C:/book2.txt",
            },
            {
                "id": "b-1",
                "chapter_id": "ch1",
                "chapter_title": "Chapter 1",
                "chunk_index": 1,
                "source_text": "src",
                "polished_translation": "Monde",
                "source_file": "C:/book2.txt",
            },
        ]
        groups = _grouped_by_source(chunks)
        self.assertEqual([k for k, _ in groups], ["C:/book1.txt", "C:/book2.txt"])
        self.assertEqual([len(v) for _, v in groups], [1, 2])

        out = _derive_output_path(Path("/tmp/out.txt"), "C:/book1.txt", 0)
        self.assertEqual(out.name, "out_book1.txt")
        out2 = _derive_output_path(Path("/tmp/out.txt"), "", 0)
        self.assertEqual(out2.name, "out.txt")

    def test_assembler_worker_writes_per_source(self) -> None:
        """End-to-end through the assembler worker, writing a temp file per source."""
        from src.backend.agents.assembler import (
            _derive_output_path,
            _grouped_by_source,
            _write_txt,
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            chunks = [
                {
                    "id": "a-0",
                    "chapter_id": "ch1",
                    "chapter_title": "Chapter 1",
                    "chunk_index": 0,
                    "source_text": "hi",
                    "polished_translation": "Bonjour",
                    "source_file": str(tmp_path / "alpha.txt"),
                },
                {
                    "id": "b-0",
                    "chapter_id": "ch1",
                    "chapter_title": "Chapter 1",
                    "chunk_index": 0,
                    "source_text": "hi",
                    "polished_translation": "Salut",
                    "source_file": str(tmp_path / "beta.txt"),
                },
            ]
            groups = _grouped_by_source(chunks)
            self.assertEqual(len(groups), 2)
            out_template = tmp_path / "out.txt"
            for source_file, group in groups:
                target = _derive_output_path(out_template, source_file, 0)
                _write_txt(target, group)
            self.assertTrue((tmp_path / "out_alpha.txt").exists())
            self.assertTrue((tmp_path / "out_beta.txt").exists())


if __name__ == "__main__":
    unittest.main()
