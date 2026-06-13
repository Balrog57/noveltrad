import tempfile
import unittest
import zipfile
from pathlib import Path

from src.backend.agents.assembler import _write_epub_from_manifest
from src.backend.formats import (
    chunk_blocks,
    chunk_paragraphs,
    prepare_project_source,
    read_document,
    write_project_manifest,
)


class FormatManifestTests(unittest.TestCase):
    def test_txt_chunks_have_stable_ids(self):
        paragraphs = [
            "Chapter One",
            "This is a long enough paragraph to form a source chunk for the first pass.",
            "This is another paragraph that should be merged or ordered deterministically.",
        ]
        first = chunk_paragraphs(paragraphs, "ch0001", "Chapter One")
        second = chunk_paragraphs(paragraphs, "ch0001", "Chapter One")
        self.assertEqual([c["id"] for c in first], [c["id"] for c in second])
        self.assertTrue(all(c["source_hash"] for c in first))

    def test_prepare_project_source_writes_manifest_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "book.txt"
            source.write_text("Chapter 1\n\nHello world.", encoding="utf-8")
            manifest = prepare_project_source(source, root / "project", "p1")
            manifest_path = write_project_manifest(root / "project", manifest)
            self.assertTrue(Path(manifest["working_source_path"]).exists())
            self.assertTrue(manifest_path.exists())
            self.assertEqual(manifest["source_format"], "txt")

    def test_epub_manifest_reinjects_translated_text(self):
        try:
            from bs4 import BeautifulSoup
            from ebooklib import epub
        except ImportError:
            self.skipTest("EPUB dependencies are not installed")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.epub"
            book = epub.EpubBook()
            book.set_identifier("sample")
            book.set_title("Sample")
            book.set_language("en")
            chapter = epub.EpubHtml(
                title="Chapter 1", file_name="chap_0001.xhtml", lang="en"
            )
            chapter.content = "<html><body><h1>Chapter 1</h1><p>Hello world.</p></body></html>"
            book.add_item(chapter)
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            book.spine = ["nav", chapter]
            book.toc = (chapter,)
            epub.write_epub(str(source), book)

            project = root / "project"
            manifest = prepare_project_source(source, project, "p1")
            doc = read_document(manifest["working_source_path"])
            chunks = []
            for chap in doc.chapters:
                chunks.extend(chunk_blocks(chap.blocks, chap.id, chap.title))
            manifest["chapters"] = [
                {"id": c.id, "title": c.title, "metadata": c.metadata}
                for c in doc.chapters
            ]
            manifest["chunks"] = [
                {
                    "id": c["id"],
                    "chapter_id": c["chapter_id"],
                    "chunk_index": c["chunk_index"],
                    "source_hash": c["source_hash"],
                    "metadata": c.get("metadata") or {},
                }
                for c in chunks
            ]
            manifest_path = write_project_manifest(project, manifest)
            translated_chunks = [
                {**c, "polished_translation": "Bonjour le monde."}
                for c in chunks
                if "Hello world" in c["source_text"]
            ]
            out = project / "target" / "out.epub"
            _write_epub_from_manifest(out, translated_chunks, manifest)
            self.assertTrue(out.exists())

            text = ""
            with zipfile.ZipFile(out) as archive:
                for name in archive.namelist():
                    if name.endswith((".html", ".xhtml")):
                        content = archive.read(name)
                        text += BeautifulSoup(content, "html.parser").get_text(" ")
            self.assertIn("Bonjour le monde.", text)


if __name__ == "__main__":
    unittest.main()
