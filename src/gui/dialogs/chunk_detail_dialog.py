"""Chunk detail dialog — read-only view of a chunk's translation history.

Shows the chain of intermediate translations (raw, glossary, qa,
grammar, polished) plus the issues flagged by each stage and quality
metrics (review score, reflection, suggestions).
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
)

from src.gui.a11y import configure
from src.gui.backend_client import BackendClient, BackendError


def _score_color(score: float | None) -> str:
    if score is None:
        return "#888"
    if score >= 8.0:
        return "#4caf50"  # green
    if score >= 6.0:
        return "#ff9800"  # orange
    return "#f44336"  # red


class ChunkDetailDialog(QDialog):
    def __init__(self, chunk_id: str, client: BackendClient, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Chunk {cid}").format(cid=chunk_id[:12]))
        self.resize(780, 640)
        self._client = client
        self._chunk_id = chunk_id
        layout = QVBoxLayout(self)

        # Header row: ID + quality score badge
        header = QHBoxLayout()
        self._header_label = QLabel(
            self.tr("<b>ID:</b> {cid}").format(cid=chunk_id)
        )
        header.addWidget(self._header_label)
        self._score_label = QLabel("")
        self._score_label.setStyleSheet(
            "font-weight: bold; font-size: 13pt; padding: 4px 10px; "
            "border-radius: 4px;"
        )
        header.addWidget(self._score_label)
        header.addStretch(1)
        reprocess_btn = QPushButton(self.tr("Reprocess"))
        reprocess_btn.clicked.connect(self._reprocess)
        configure(
            reprocess_btn,
            name=self.tr("Reprocess chunk"),
            tooltip=self.tr("Send this chunk back through the pipeline."),
        )
        header.addWidget(reprocess_btn)
        layout.addLayout(header)

        self._tabs = QTabWidget()
        for label in (
            self.tr("Source"),
            self.tr("Raw (NLLB)"),
            self.tr("Glossary"),
            self.tr("QA"),
            self.tr("Grammar"),
            self.tr("Polished"),
            self.tr("Quality"),
            self.tr("Status"),
        ):
            self._tabs.addTab(QTextEdit(), label)
        layout.addWidget(self._tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.refresh()

    def _set_text(self, idx: int, text: str) -> None:
        w = self._tabs.widget(idx)
        if isinstance(w, QTextEdit):
            w.setPlainText(text or self.tr("(empty)"))

    def _build_quality_text(self, c: dict[str, Any]) -> str:
        """Assemble a human-readable quality report from the chunk data."""
        parts: list[str] = []

        # Review score
        score = c.get("review_score")
        if score is not None:
            parts.append(f"=== REVIEW SCORE: {score}/10 ===")

        # Reflection from LLM polisher
        reflection = c.get("reflection") or ""
        if reflection:
            parts.append(f"\n=== REFLECTION ===\n{reflection}")

        # Suggestions from LLM polisher
        suggestions = c.get("suggestions") or []
        if suggestions:
            parts.append("\n=== SUGGESTIONS ===")
            for i, s in enumerate(suggestions, 1):
                span = s.get("span", "") or ""
                issue = s.get("issue", "") or ""
                fix = s.get("fix", "") or ""
                parts.append(f"\n{i}. [{span}] {issue}")
                if fix:
                    parts.append(f"   Fix: {fix}")

        # Review annotations (from the Reviewer agent)
        annotations = c.get("review_annotations") or []
        if annotations:
            parts.append("\n=== REVIEWER ANNOTATIONS ===")
            for i, a in enumerate(annotations, 1):
                atype = a.get("type", "") or ""
                span = a.get("span", "") or ""
                suggestion = a.get("suggestion", "") or ""
                parts.append(f"\n{i}. [{atype}] {span}: {suggestion}")

        # Issues summary counts
        issues_parts: list[str] = []
        qa = c.get("qa_issues") or []
        gm = c.get("grammar_issues") or []
        cf = c.get("consistency_flags") or []
        counts = []
        if qa:
            counts.append(f"QA: {len(qa)}")
        if gm:
            counts.append(f"Grammar: {len(gm)}")
        if cf:
            counts.append(f"Consistency: {len(cf)}")
        if counts:
            issues_parts.append(f"\n=== ISSUES ===\n{'  |  '.join(counts)}")

        # Detailed issues
        if qa:
            issues_parts.append("\n--- QA Issues ---")
            for e in qa[:10]:
                issues_parts.append(
                    f"  [{e.get('severity','info')}] {str(e.get('message',''))[:150]}"
                )
        if gm:
            issues_parts.append("\n--- Grammar Issues ---")
            for e in gm[:10]:
                issues_parts.append(
                    f"  [{e.get('rule','')}] {str(e.get('message',''))[:150]}"
                )
        if cf:
            issues_parts.append("\n--- Consistency Flags ---")
            for e in cf[:5]:
                issues_parts.append(f"  {str(e.get('message',''))[:150]}")

        parts.extend(issues_parts)

        return "\n".join(parts) if parts else self.tr("No quality data available.")

    def refresh(self) -> None:
        try:
            c = self._client.get(f"/chunks/{self._chunk_id}", timeout=5.0)
        except BackendError as exc:
            self._set_text(0, self.tr("Backend error: {err}").format(err=exc))
            return
        if not c:
            return

        # Update score badge
        score = c.get("review_score")
        if score is not None:
            color = _score_color(score)
            self._score_label.setText(self.tr("Score: {s}/10").format(s=score))
            self._score_label.setStyleSheet(
                f"font-weight: bold; font-size: 13pt; padding: 4px 10px; "
                f"border-radius: 4px; background-color: {color}; color: white;"
            )
            self._score_label.setVisible(True)
        else:
            self._score_label.setVisible(False)

        self._set_text(0, c.get("source_text", ""))
        self._set_text(1, c.get("raw_translation", ""))
        self._set_text(2, c.get("glossary_applied", ""))
        self._set_text(3, c.get("qa_checked", ""))
        self._set_text(4, c.get("grammar_checked", ""))
        self._set_text(5, c.get("polished_translation", ""))
        self._set_text(6, self._build_quality_text(c))

        meta = (
            self.tr("Status: {status}\n").format(status=c.get("status", ""))
            + self.tr("Chapter: {chapter}\n").format(
                chapter=c.get("chapter_title") or c.get("chapter_id", "")
            )
            + self.tr("Chunk #: {n}\n").format(n=c.get("chunk_index", ""))
            + self.tr("Source hash: {h}\n").format(h=c.get("source_hash", ""))
            + self.tr("Error: {err}").format(
                err=c.get("error_message") or "none"
            )
        )
        self._set_text(7, meta)

    def _reprocess(self) -> None:
        try:
            self._client.post(
                f"/chunks/{self._chunk_id}/reprocess", timeout=5.0
            )
        except BackendError as exc:
            self._set_text(7, self.tr("Reprocess failed: {err}").format(err=exc))
            return
        self._set_text(7, self.tr("Reprocess queued."))
        self.refresh()


__all__ = ["ChunkDetailDialog"]
