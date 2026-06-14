"""HITL popup — non-blocking notification when the pipeline needs input."""

from __future__ import annotations

import logging
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.gui.backend_client import BackendClient, BackendError
from src.gui.a11y import configure

logger = logging.getLogger(__name__)


class HITLPopup(QDialog):
    def __init__(
        self,
        request_id: str,
        chunk_id: str,
        stage: str,
        issue: dict[str, Any],
        client: BackendClient,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(self.tr("HITL — {stage}").format(stage=stage))
        self.setModal(False)
        self._request_id = request_id
        self._client = client
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self.tr("<b>Chunk:</b> {cid}").format(cid=chunk_id[:12])))
        layout.addWidget(QLabel(self.tr("<b>Stage:</b> {stage}").format(stage=stage)))
        priority = issue.get("priority", "ISSUE")
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            self.tr("Priority: {priority}\n\n{explanation}\n\n").format(
                priority=priority, explanation=issue.get("explanation", "")
            )
            + self.tr("Quote: {quote}").format(quote=issue.get("quote", ""))
        )
        text.setMaximumHeight(180)
        layout.addWidget(text)
        layout.addWidget(QLabel(self.tr("Your answer:")))
        self._answer = QLineEdit()
        configure(
            self._answer,
            name=self.tr("Your answer"),
            description=self.tr("Enter your correction or instruction for the AI here."),
        )
        layout.addWidget(self._answer)
        row = QHBoxLayout()
        row.addStretch(1)
        skip_btn = QPushButton(self.tr("Skip"))
        skip_btn.clicked.connect(self.reject)
        configure(
            skip_btn,
            name=self.tr("Skip"),
            tooltip=self.tr("Skip this issue"),
            shortcut="Esc",
        )
        row.addWidget(skip_btn)
        send_btn = QPushButton(self.tr("Send"))
        send_btn.clicked.connect(self._send)
        send_btn.setDefault(True)
        configure(
            send_btn,
            name=self.tr("Send"),
            tooltip=self.tr("Submit your answer"),
            shortcut="Ctrl+Return",
        )
        row.addWidget(send_btn)
        layout.addLayout(row)

    def _send(self) -> None:
        answer = self._answer.text().strip()
        if not answer:
            return
        try:
            self._client.post(
                "/hltl/respond",
                body={"request_id": self._request_id, "answer": answer},
                timeout=5.0,
            )
        except BackendError as exc:
            logger.warning("HITL respond failed: %s", exc)
        self.accept()


__all__ = ["HITLPopup"]
