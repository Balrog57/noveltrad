"""Tests for the lexicon hard-delete behaviour.

Covers:
  * hard delete actually removes the row (GET /lexicon omits it);
  * deleting an unknown term returns 404;
  * re-creating the same source after delete yields a new term id.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.backend.server import create_app


def _make_client() -> TestClient:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    app = create_app(db_path=root / ".state.db", vector_dir=root / ".vectors")
    return TestClient(app)


class LexiconHardDeleteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._client = _make_client()

    def test_hard_delete_removes_row(self) -> None:
        # Create a term.
        res = self._client.post(
            "/lexicon",
            json={"source": "魔法", "target": "magie", "category": "other"},
        )
        self.assertEqual(res.status_code, 200, res.text)
        term_id = res.json()["id"]
        # Sanity: it's listed.
        before = self._client.get("/lexicon").json()["terms"]
        self.assertEqual([t["id"] for t in before], [term_id])
        # Hard delete.
        res = self._client.delete(f"/lexicon/{term_id}")
        self.assertEqual(res.status_code, 200, res.text)
        # After: gone from the listing.
        after = self._client.get("/lexicon").json()["terms"]
        self.assertEqual(after, [])

    def test_delete_nonexistent_returns_404(self) -> None:
        res = self._client.delete("/lexicon/does-not-exist")
        self.assertEqual(res.status_code, 404, res.text)

    def test_delete_then_recreate_works(self) -> None:
        first = self._client.post(
            "/lexicon",
            json={"source": "hero", "target": "héros", "category": "other"},
        )
        first_id = first.json()["id"]
        self._client.delete(f"/lexicon/{first_id}")
        # Re-create the same source — should yield a new id and be present.
        second = self._client.post(
            "/lexicon",
            json={"source": "hero", "target": "héros", "category": "other"},
        )
        self.assertEqual(second.status_code, 200, second.text)
        second_id = second.json()["id"]
        self.assertNotEqual(second_id, first_id)
        listed = self._client.get("/lexicon").json()["terms"]
        self.assertEqual([t["id"] for t in listed], [second_id])


if __name__ == "__main__":
    unittest.main()
