"""
Widget de Chat contextuel IA pour NovelTrad.
Interface de chat intégrée dans le panneau droit pour interagir avec le LLM.
Conforme au cahier des charges §10.3.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QScrollArea, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor


class ChatMessage(QFrame):
    """A single chat message bubble."""

    def __init__(self, text, is_user=True, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        # Role label
        role = QLabel("Vous" if is_user else "IA")
        role.setStyleSheet(
            f"font-weight: bold; font-size: 11px; "
            f"color: {'#60a5fa' if is_user else '#a78bfa'};"
        )
        layout.addWidget(role)

        # Message text
        msg = QLabel(text)
        msg.setWordWrap(True)
        msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg.setStyleSheet("font-size: 13px; padding: 4px 0;")
        layout.addWidget(msg)

        bg = "#1e3a5f" if is_user else "#2d1f4e"
        self.setStyleSheet(f"""
            ChatMessage {{
                background-color: {bg};
                border-radius: 8px;
                margin: 2px {'24px 2px 4px' if is_user else '4px 2px 24px'};
            }}
        """)


class AIWorker(QThread):
    """Worker thread for AI chat responses."""
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, engine, messages, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.messages = messages

    def run(self):
        try:
            if self.engine and self.engine.client:
                response = self.engine.client.chat.completions.create(
                    model=self.engine.model,
                    messages=self.messages,
                    temperature=0.7,
                    max_tokens=1024,
                )
                self.response_ready.emit(response.choices[0].message.content)
            else:
                self.error_occurred.emit("Aucun moteur IA configuré.")
        except Exception as e:
            self.error_occurred.emit(str(e))


class ChatWidget(QWidget):
    """
    Chat widget for contextual AI interaction.
    Integrates with the current segment for context-aware conversations.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.llm_engine = None
        self.current_context = {}  # {source_text, target_text, chapter_title}
        self.conversation_history = []
        self.worker = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Chat history area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setSpacing(4)
        self.scroll_area.setWidget(self.chat_container)
        layout.addWidget(self.scroll_area, 1)

        # Quick action buttons
        actions_layout = QHBoxLayout()
        actions = [
            ("💡 Expliquer", "Explique ce passage et son contexte culturel."),
            ("✏️ Alternatives", "Propose 3 traductions alternatives pour ce segment."),
            ("📖 Résumer", "Résume le contexte narratif de ce chapitre."),
        ]
        for label, prompt in actions:
            btn = QPushButton(label)
            btn.setStyleSheet("font-size: 11px; padding: 4px 8px;")
            btn.clicked.connect(lambda checked, p=prompt: self._send_quick_action(p))
            actions_layout.addWidget(btn)
        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # Input area
        input_layout = QHBoxLayout()
        self.input_field = QTextEdit()
        self.input_field.setMaximumHeight(60)
        self.input_field.setPlaceholderText("Posez une question sur le texte…")
        input_layout.addWidget(self.input_field, 1)

        self.send_btn = QPushButton("▶")
        self.send_btn.setStyleSheet(
            "background-color: #3b82f6; color: white; "
            "font-size: 16px; padding: 8px 14px; border-radius: 6px;"
        )
        self.send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(self.send_btn)

        layout.addLayout(input_layout)

        # Clear button
        clear_btn = QPushButton("🗑 Effacer l'historique")
        clear_btn.setStyleSheet("font-size: 11px; color: #94a3b8;")
        clear_btn.clicked.connect(self._clear_history)
        layout.addWidget(clear_btn)

    def set_engine(self, llm_engine):
        """Set the LLM engine for chat."""
        self.llm_engine = llm_engine

    def set_context(self, source_text='', target_text='', chapter_title=''):
        """Update the current context for contextual queries."""
        self.current_context = {
            'source_text': source_text,
            'target_text': target_text,
            'chapter_title': chapter_title,
        }

    def _send_message(self):
        text = self.input_field.toPlainText().strip()
        if not text:
            return

        self.input_field.clear()
        self._add_message(text, is_user=True)
        self._get_ai_response(text)

    def _send_quick_action(self, prompt):
        self._add_message(prompt, is_user=True)
        self._get_ai_response(prompt)

    def _add_message(self, text, is_user=True):
        msg = ChatMessage(text, is_user=is_user)
        self.chat_layout.addWidget(msg)

        # Scroll to bottom
        sb = self.scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _get_ai_response(self, user_message):
        """Send message to AI with context."""
        if not self.llm_engine:
            self._add_message("⚠️ Aucun moteur IA configuré. Vérifiez les paramètres.", is_user=False)
            return

        # Build system prompt with context
        system_prompt = "Tu es un assistant de traduction spécialisé dans les romans et web novels."
        if self.current_context.get('source_text'):
            system_prompt += f"\n\nContexte actuel :\n- Chapitre : {self.current_context.get('chapter_title', 'N/A')}"
            system_prompt += f"\n- Texte source : {self.current_context['source_text'][:500]}"
            if self.current_context.get('target_text'):
                system_prompt += f"\n- Traduction actuelle : {self.current_context['target_text'][:500]}"

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 10 messages)
        for msg in self.conversation_history[-10:]:
            messages.append(msg)

        messages.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "user", "content": user_message})

        # Disable send while processing
        self.send_btn.setEnabled(False)
        self.send_btn.setText("⏳")

        self.worker = AIWorker(self.llm_engine, messages)
        self.worker.response_ready.connect(self._on_response)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    @pyqtSlot(str)
    def _on_response(self, response):
        self._add_message(response, is_user=False)
        self.conversation_history.append({"role": "assistant", "content": response})

    @pyqtSlot(str)
    def _on_error(self, error):
        self._add_message(f"❌ Erreur : {error}", is_user=False)

    def _on_finished(self):
        self.send_btn.setEnabled(True)
        self.send_btn.setText("▶")

    def _clear_history(self):
        self.conversation_history.clear()
        # Remove all chat messages
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
