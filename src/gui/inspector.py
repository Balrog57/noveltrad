"""Multi-agent inspection panel (CDC F1.b).

Accordion-style panel showing, per agent:
  - status chip (pending / running / done)
  - the structured payload (edits_made / glossary_matches / flags) as a table
  - a CoT/log area

Toggle "Vue simplifiée" hides the detail tables, leaving only status chips.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Pipeline stages in order, with display labels.
STAGES: list[tuple[str, str]] = [
    ("translator", "1. Traducteur"),
    ("proofreader", "2. Relecture & Grammaire"),
    ("glossary", "3. Cohérence & Glossaire"),
    ("validator", "4. Validateur / Arbitre"),
]

# Columns shown in the per-stage detail table.
STAGE_COLUMNS: dict[str, list[str]] = {
    "translator": ["Texte produit"],
    "proofreader": ["Type", "Phrase d'origine", "Phrase corrigée", "Raison"],
    "glossary": ["Terme source", "Traduction imposée", "Statut"],
    "validator": ["Sévérité", "Problème", "Résolution"],
}


class StageWidget(QFrame):
    """One collapsible block per agent."""

    def __init__(self, stage_id: str, label: str) -> None:
        super().__init__()
        self.stage_id = stage_id
        self.setFrameShape(QFrame.Shape.Box)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        # Header: label + status chip + expand toggle.
        header = QHBoxLayout()
        self.title = QLabel(f"<b>{label}</b>")
        self.status_chip = QLabel("○")
        self.status_chip.setStyleSheet("color: gray; font-weight: bold;")
        self.expand_btn = QPushButton("▾")
        self.expand_btn.setFixedWidth(24)
        self.expand_btn.setCheckable(True)
        self.expand_btn.setChecked(True)
        self.expand_btn.toggled.connect(self._on_toggle)

        header.addWidget(self.expand_btn)
        header.addWidget(self.title, 1)
        header.addWidget(self.status_chip)
        layout.addLayout(header)

        # Detail table.
        cols = STAGE_COLUMNS.get(stage_id, ["—"])
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        # Text preview (translator produces text, others show a preview too).
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(90)
        self.preview.setPlaceholderText("Texte produit par cet agent…")
        layout.addWidget(self.preview)

        self._detail_visible = True

    def set_status(self, status: str) -> None:
        glyphs = {"pending": ("○", "gray"), "running": ("⏳", "#cc8800"), "done": ("✓", "green"),
                  "error": ("✗", "red")}
        glyph, color = glyphs.get(status, ("○", "gray"))
        self.status_chip.setText(glyph)
        self.status_chip.setStyleSheet(f"color: {color}; font-weight: bold;")

    def populate(self, payload: dict[str, Any]) -> None:
        """Fill the table + preview from a stage payload (worker.stage_output)."""
        text = payload.get("text")
        if text:
            self.preview.setPlainText(text)

        items = payload.get("items") or []
        col_map = {
            "proofreader": lambda it: [it.get("type", ""), it.get("original_phrase", ""),
                                       it.get("revised_phrase", ""), it.get("reason", "")],
            "glossary": lambda it: [it.get("source_term", ""),
                                    it.get("forced_target_term", ""), it.get("status", "")],
            "validator": lambda it: [it.get("severity", ""), it.get("issue", ""),
                                     it.get("resolution", "")],
            "translator": lambda it: [],
        }
        mapper = col_map.get(self.stage_id)
        if not mapper:
            return
        self.table.setRowCount(0)
        for it in items:
            row = mapper(it)
            if not row:
                continue
            r = self.table.rowCount()
            self.table.insertRow(r)
            for c, val in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(str(val)))

        # Validator: surface the score in the title.
        if self.stage_id == "validator":
            score = payload.get("fidelity_score")
            stat = payload.get("status")
            extra = []
            if score is not None:
                extra.append(f"fidelity {score}")
            if stat:
                extra.append(stat)
            if extra:
                self.title.setText(self.title.text().split(" — ")[0] + f" — {', '.join(extra)}")

    def _on_toggle(self, checked: bool) -> None:
        self.expand_btn.setText("▾" if checked else "▸")
        self.table.setVisible(checked)
        self.preview.setVisible(checked)


class InspectorPanel(QWidget):
    """The full inspector: 4 stage blocks + a global log + simplified toggle."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        # Top bar: title + simplified-view toggle.
        top = QHBoxLayout()
        top.addWidget(QLabel("<b>Inspecteur du pipeline</b>"))
        top.addStretch()
        self.simple_btn = QPushButton("Vue simplifiée")
        self.simple_btn.setCheckable(True)
        self.simple_btn.toggled.connect(self.toggle_simple)
        top.addWidget(self.simple_btn)
        layout.addLayout(top)

        self.stages: dict[str, StageWidget] = {}
        for sid, label in STAGES:
            sw = StageWidget(sid, label)
            self.stages[sid] = sw
            layout.addWidget(sw)

        # Global log area.
        layout.addWidget(QLabel("Journal"))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Étapes du pipeline multi-agent…")
        layout.addWidget(self.log_view, 1)

        for sid, _ in STAGES:
            self.stages[sid].set_status("pending")

    def reset(self) -> None:
        self.log_view.clear()
        for sid, _ in STAGES:
            self.stages[sid].set_status("pending")
            self.stages[sid].table.setRowCount(0)
            self.stages[sid].preview.clear()

    def mark_running(self, stage_id: str) -> None:
        if stage_id in self.stages:
            self.stages[stage_id].set_status("running")

    def mark_done(self, stage_id: str) -> None:
        if stage_id in self.stages:
            self.stages[stage_id].set_status("done")

    def append_log(self, msg: str) -> None:
        self.log_view.append(msg)

    def populate_stage(self, stage_id: str, payload: dict[str, Any]) -> None:
        if stage_id in self.stages:
            self.stages[stage_id].populate(payload)

    def toggle_simple(self, simple: bool) -> None:
        """F1.b: hide detail tables for a 'simplified' view (status chips only)."""
        for sw in self.stages.values():
            sw.table.setVisible(not simple)
            sw.preview.setVisible(not simple)
        self.log_view.setVisible(not simple)
        self.simple_btn.setText("Vue détaillée" if simple else "Vue simplifiée")
