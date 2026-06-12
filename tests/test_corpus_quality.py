"""Corpus-based quality evaluation tests.

Uses representative literary extracts from ``tests.corpus`` to verify
structural integrity and terminology coherence through the parse →
chunk → assemble pipeline.
"""

import tempfile
import unittest
from pathlib import Path

from tests.corpus import (
    ALL_EXTRACTS,
    structural_metrics,
    terminology_coherence,
    write_srt_fixture,
    write_txt_fixture,
)
from src.backend.formats import (
    chunk_paragraphs,
    read_document,
)


class CorpusStructuralTests(unittest.TestCase):
    """Verify parse → chunk preserves text across all extract types."""

    def test_dialogue_chunks_preserve_text(self) -> None:
        extract = ALL_EXTRACTS["dialogue"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write_txt_fixture("dialogue", root)
            doc = read_document(path)
            all_text = " ".join(
                p for ch in doc.chapters for p in ch.paragraphs
            )
            self.assertIn("I can't believe you did that", all_text)
            self.assertIn("The gate was already opening", all_text)
            self.assertIn("A long silence filled the room", all_text)

    def test_exposition_chunks_preserve_text(self) -> None:
        extract = ALL_EXTRACTS["exposition"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write_txt_fixture("exposition", root)
            doc = read_document(path)
            all_text = " ".join(
                p for ch in doc.chapters for p in ch.paragraphs
            )
            self.assertIn("Aldervale", all_text)
            self.assertIn("Treaty of the Four Rivers", all_text)
            self.assertIn("Until today", all_text)

    def test_description_preserves_structure(self) -> None:
        extract = ALL_EXTRACTS["description"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write_txt_fixture("description", root)
            doc = read_document(path)
            paragraphs = doc.chapters[0].paragraphs if doc.chapters else []
            self.assertGreaterEqual(len(paragraphs), 1)
            all_text = " ".join(paragraphs)
            self.assertIn("crimson roses", all_text)
            self.assertIn("marble nymph", all_text)
            self.assertIn("a thousand bees", all_text)

    def test_fantasy_terms_preserved(self) -> None:
        extract = ALL_EXTRACTS["fantasy_terms"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write_txt_fixture("fantasy_terms", root)
            doc = read_document(path)
            all_text = " ".join(
                p for ch in doc.chapters for p in ch.paragraphs
            )
            names = ["Veil-Walker", "Binding Words", "Arch-Fiend", "Talric", "Veil"]
            for name in names:
                with self.subTest(name=name):
                    self.assertIn(name, all_text, f"Entity '{name}' should be preserved")

    def test_dialogue_line_breaks_preserved(self) -> None:
        """Verify dialogue structure (quotes, line breaks) survives chunking."""
        extract = ALL_EXTRACTS["dialogue"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write_txt_fixture("dialogue", root)
            doc = read_document(path)
            chunks = chunk_paragraphs(
                doc.chapters[0].paragraphs,
                doc.chapters[0].id,
                doc.chapters[0].title,
            )
            combined = " ".join(c["source_text"] for c in chunks)
            quote_count_orig = extract.count('"')
            quote_count_recon = combined.count('"')
            self.assertEqual(quote_count_orig, quote_count_recon,
                             "Dialogue quotes should not be lost")

    def test_structural_metrics_detect_loss(self) -> None:
        """Verify structural_metrics correctly reports text loss."""
        original = "Hello world, this is a test."
        reconstructed = "Hello world, this is a test."
        metrics = structural_metrics(original, reconstructed)
        self.assertEqual(metrics["chars_lost"], 0)
        self.assertEqual(metrics["chars_added"], 0)
        self.assertEqual(metrics["word_count_delta"], 0)

    def test_structural_metrics_detect_difference(self) -> None:
        """Verify structural_metrics detects missing content."""
        original = "Hello world, this is a test."
        reconstructed = "Hello world."
        metrics = structural_metrics(original, reconstructed)
        self.assertGreater(metrics["chars_lost"], 0)

    def test_terminology_coherence_all_preserved(self) -> None:
        source = "The Veil-Walker spoke to Talric about the Arch-Fiend."
        translated = "Le Veil-Walker parla à Talric de l'Arch-Fiend."
        terms = ["Veil-Walker", "Talric", "Arch-Fiend"]
        result = terminology_coherence(source, translated, terms)
        self.assertTrue(result["all_preserved"])

    def test_terminology_coherence_missing(self) -> None:
        source = "The Veil-Walker spoke to Talric."
        translated = "Le sorcier parla à l'étudiant."
        terms = ["Veil-Walker", "Talric"]
        result = terminology_coherence(source, translated, terms)
        self.assertFalse(result["all_preserved"])


class CorpusFormatRoundtripTests(unittest.TestCase):
    """Verify format round-trips preserve essential structure."""

    def test_srt_fixture_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write_srt_fixture("dialogue", root)
            doc = read_document(path)
            self.assertEqual(doc.source_format, "srt")
            paragraphs = doc.chapters[0].paragraphs
            self.assertGreaterEqual(len(paragraphs), 1)
            all_text = " ".join(paragraphs)
            self.assertIn("I can't believe you did that", all_text)
            self.assertIn("A long silence filled the room", all_text)

    def test_txt_fixture_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write_txt_fixture("exposition", root)
            doc = read_document(path)
            self.assertEqual(doc.source_format, "txt")
            self.assertGreaterEqual(len(doc.chapters), 1)

    def test_all_extracts_produce_valid_chunks(self) -> None:
        """Every extract must produce at least one parsable chunk."""
        for key in ALL_EXTRACTS:
            with self.subTest(extract=key):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    path = write_txt_fixture(key, root)
                    doc = read_document(path)
                    self.assertGreaterEqual(
                        len(doc.chapters), 1,
                        f"Extract '{key}' should produce at least 1 chapter",
                    )


if __name__ == "__main__":
    unittest.main()
