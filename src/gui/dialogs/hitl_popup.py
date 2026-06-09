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
        self.setWindowTitle(f"HITL — {stage}")
        self.setModal(False)
        self._request_id = request_id
        self._client = client
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>Chunk:</b> {chunk_id[:12]}"))
        layout.addWidget(QLabel(f"<b>Stage:</b> {stage}"))
        priority = issue.get("priority", "ISSUE")
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            f"Priority: {priority}\n\n{issue.get('explanation', '')}\n\n"
            f"Quote: {issue.get('quote', '')}"
        )
        text.setMaximumHeight(180)
        layout.addWidget(text)
        layout.addWidget(QLabel("Your answer:"))
        self._answer = QLineEdit()
        layout.addWidget(self._answer)
        row = QHBoxLayout()
        row.addStretch(1)
        skip_btn = QPushButton("Skip")
        skip_btn.clicked.connect(self.reject)
        row.addWidget(skip_btn)
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self._send)
        send_btn.setDefault(True)
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
