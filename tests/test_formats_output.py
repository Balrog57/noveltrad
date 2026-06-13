"""Tests for assembler output formats.

These tests use the ``Worker`` class directly with a small in-memory
chunk list and do not spawn worker processes or LLM calls.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.backend.agents.assembler import Worker as AssemblerWorker, _polished_text
from src.backend.agents.base_worker import make_task_message
from src.backend.formats import write_project_manifest


def _make_worker() -> AssemblerWorker:
    import queue

    return AssemblerWorker(
        stage="assembler",
        input_queue=queue.Queue(),
        output_queue=queue.Queue(),
        control_queue=queue.Queue(),
        worker_id="asm-test",
    )


def _sample_chunks(source_format: str = "txt") -> list[dict]:
    # No source_file so the assembler writes to the requested output path.
    return [
        {
            "id": "c1",
            "chapter_id": "ch1",
            "chapter_title": "Chapter 1",
            "chunk_index": 0,
            "source_text": "Hello, world.",
            "raw_translation": "Bonjour, le monde.",
            "polished_translation": "Bonjour, le monde poli.",
            "metadata": {},
        },
        {
            "id": "c2",
            "chapter_id": "ch1",
            "chapter_title": "Chapter 1",
            "chunk_index": 1,
            "source_text": "A second sentence.",
            "raw_translation": "Une deuxième phrase.",
            "grammar_checked": "Une deuxième phrase corrigée.",
            "polished_translation": "Une deuxième phrase polie.",
            "metadata": {},
        },
    ]


def _make_assemble_task(chunks: list[dict], output_path: Path, fmt: str, manifest_path: Path | None = None) -> dict:
    return make_task_message(
        chunk_id="assemble-1",
        action="assemble",
        payload={
            "chunks": chunks,
            "output_path": str(output_path),
            "format": fmt,
            "title": "Test Book",
            "manifest_path": str(manifest_path) if manifest_path else None,
        },
    )


class OutputFormatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.worker = _make_worker()

    def _run_assemble(self, chunks: list[dict], out: Path, fmt: str, manifest_path: Path | None = None) -> dict:
        msg = _make_assemble_task(chunks, out, fmt, manifest_path=manifest_path)
        # read emitted message off the worker's output queue.
        result = self.worker.handle_task(msg)
        # handle_task puts the response on the output queue and returns None.
        if result is None:
            try:
                result = self.worker.output_queue.get(timeout=2.0)
            except Exception as exc:
                self.fail(f"assembler did not emit a response: {exc}")
        return result

    def test_txt_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "out.txt"
            chunks = _sample_chunks()
            result = self._run_assemble(chunks, out, "txt")
            self.assertEqual(result.get("type"), "done")
            self.assertEqual(result["payload"].get("status"), "assembled")
            self.assertTrue(out.exists())
            text = out.read_text(encoding="utf-8")
            self.assertIn("Chapter 1", text)
            self.assertIn(_polished_text(chunks[0]), text)
            self.assertIn(_polished_text(chunks[1]), text)

    def test_docx_output(self) -> None:
        try:
            import docx  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("python-docx not installed")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "out.docx"
            result = self._run_assemble(_sample_chunks(), out, "docx")
            self.assertEqual(result["payload"].get("status"), "assembled")
            self.assertTrue(out.exists())

            d = docx.Document(str(out))
            full_text = "\n".join(p.text for p in d.paragraphs)
            self.assertIn("Chapter 1", full_text)
            self.assertIn(_polished_text(_sample_chunks()[1]), full_text)

    def test_srt_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "out.srt"
            result = self._run_assemble(_sample_chunks(), out, "srt")
            self.assertEqual(result["payload"].get("status"), "assembled")
            self.assertTrue(out.exists())
            text = out.read_text(encoding="utf-8")
            self.assertIn("1", text)
            self.assertIn(" --> ", text)
            self.assertIn(_polished_text(_sample_chunks()[0]), text)

    def test_epub_output(self) -> None:
        try:
            import ebooklib
            from ebooklib import epub
        except ImportError:
            raise unittest.SkipTest("EbookLib not installed")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "out.epub"
            result = self._run_assemble(_sample_chunks(), out, "epub")
            self.assertEqual(result["payload"].get("status"), "assembled")
            self.assertTrue(out.exists())

            book = epub.read_epub(str(out), options={"ignore_ncx": True})
            items = [i for i in book.get_items() if i.get_type() == ebooklib.ITEM_DOCUMENT]
            self.assertTrue(items)

    def test_epub_bilingual_output(self) -> None:
        try:
            import ebooklib
            from ebooklib import epub
            from bs4 import BeautifulSoup  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("EPUB dependencies not installed")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "out_bilingual.epub"
            result = self._run_assemble(_sample_chunks(), out, "epub_bilingual")
            self.assertEqual(result["payload"].get("status"), "assembled")
            self.assertTrue(out.exists())

            book = epub.read_epub(str(out), options={"ignore_ncx": True})
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    soup = BeautifulSoup(item.get_content(), "html.parser")
                    originals = soup.find_all("p", class_="original")
                    translations = soup.find_all("p", class_="translation")
                    if originals and translations:
                        self.assertGreaterEqual(len(originals), 1)
                        self.assertGreaterEqual(len(translations), 1)
                        return
            self.fail("bilingual EPUB did not contain original/translation paragraphs")

    def test_epub_from_manifest_preserves_structure(self) -> None:
        try:
            import ebooklib
            from ebooklib import epub
            from bs4 import BeautifulSoup  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("EPUB dependencies not installed")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Build a minimal source EPUB with one chapter.
            book = epub.EpubBook()
            book.set_identifier("src-id")
            book.set_title("Source Book")
            book.set_language("en")
            chapter = epub.EpubHtml(title="Ch1", file_name="ch1.xhtml", lang="en")
            chapter.content = (
                "<html><head><title>Ch1</title></head>"
                "<body><p>Hello, world.</p><p>A second sentence.</p></body></html>"
            )
            book.add_item(chapter)
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            book.spine = ["nav", chapter]
            book.toc = (chapter,)
            source_epub = root / "source.epub"
            epub.write_epub(str(source_epub), book)

            project_dir = root / "project"
            manifest = {
                "project_id": "manifest-test",
                "source_format": "epub",
                "source_path": str(source_epub),
                "working_source_path": str(source_epub),
                "target_path": str(project_dir / "target.epub"),
                "chapters": [],
                "chunks": [],
                "format_payload": {},
            }
            manifest_path = write_project_manifest(project_dir, manifest)

            # Chunks must carry epub anchors that match the source document.
            chunks = [
                {
                    "id": "c1",
                    "chapter_id": "ch1",
                    "chapter_title": "Chapter 1",
                    "chunk_index": 0,
                    "source_text": "Hello, world.",
                    "raw_translation": "Bonjour, le monde.",
                    "metadata": {
                        "anchors": [
                            {"kind": "epub_text_node", "item_id": "ch1", "href": "ch1.xhtml", "node_index": 0}
                        ]
                    },
                },
                {
                    "id": "c2",
                    "chapter_id": "ch1",
                    "chapter_title": "Chapter 1",
                    "chunk_index": 1,
                    "source_text": "A second sentence.",
                    "raw_translation": "Une deuxième phrase.",
                    "metadata": {
                        "anchors": [
                            {"kind": "epub_text_node", "item_id": "ch1", "href": "ch1.xhtml", "node_index": 1}
                        ]
                    },
                },
            ]
            out = project_dir / "target.epub"
            result = self._run_assemble(chunks, out, "epub", manifest_path=manifest_path)
            self.assertEqual(result["payload"].get("status"), "assembled")
            self.assertTrue(out.exists())

            assembled = epub.read_epub(str(out), options={"ignore_ncx": True})
            for item in assembled.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    soup = BeautifulSoup(item.get_content(), "html.parser")
                    text = soup.get_text(" ", strip=True)
                    if "Bonjour" in text or "deuxième" in text:
                        self.assertIn("Bonjour", text)
                        self.assertIn("deuxième", text)
                        return
            self.fail("translated text not found in manifest-based EPUB")

    def test_missing_output_path_returns_error(self) -> None:
        msg = make_task_message(chunk_id="assemble-2", action="assemble", payload={"chunks": []})
        result = self.worker.handle_task(msg)
        if result is None:
            result = self.worker.output_queue.get(timeout=2.0)
        self.assertEqual(result.get("type"), "error")


if __name__ == "__main__":
    unittest.main()
