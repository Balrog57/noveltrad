"""
Dialog pour éditer les instructions personnalisées (M10).
Permet de définir du contexte global pour l'IA (Ton, Style, Glossaire implicite).
Conforme au cahier des charges §13.2 (M10).
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QMessageBox
)

class CustomInstructionsDialog(QDialog):
    """Dialog to edit project-level custom instructions for AI."""

    def __init__(self, parent=None, current_instructions=None):
        super().__init__(parent)
        self.setWindowTitle("Instructions Personnalisées (IA)")
        self.resize(600, 450)
        self.instructions = current_instructions or ""

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Header / Explanation
        info_lbl = QLabel(
            "Définissez ici des instructions globales qui seront envoyées à l'IA "
            "pour chaque traduction.\n"
            "Utile pour préciser le ton, le style narratif, ou des règles de formatage."
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: #64748b; margin-bottom: 10px;")
        layout.addWidget(info_lbl)

        # Template Selector
        tpl_layout = QHBoxLayout()
        tpl_layout.addWidget(QLabel("Modèles rapides :"))
        self.tpl_combo = QComboBox()
        self.tpl_combo.addItems([
            "Sélectionner un modèle...",
            "Roman Fantasy (Épique)",
            "Roman Policier (Sérieux)",
            "Web Novel (Familier)",
            "Technique / Manuel",
            "Maintien des suffixe (San, Kun...)"
        ])
        self.tpl_combo.currentTextChanged.connect(self._apply_template)
        tpl_layout.addWidget(self.tpl_combo)
        tpl_layout.addStretch()
        layout.addLayout(tpl_layout)

        # Editor
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "Exemple : 'Le protagoniste est sarcastique. Utilise un langage soutenu pour la narration "
            "mais familier pour les dialogues. Ne traduis pas les noms de sorts.'"
        )
        self.text_edit.setPlainText(self.instructions)
        layout.addWidget(self.text_edit)

        # Footer Actions
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Enregistrer")
        save_btn.setStyleSheet("background-color: #3b82f6; color: white; font-weight: bold;")
        save_btn.clicked.connect(self._save)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _apply_template(self, text):
        """Insert template text."""
        templates = {
            "Roman Fantasy (Épique)": "Style épique et descriptif. Vocabulaire archaïque modéré. Garde la majesté des dialogues.",
            "Roman Policier (Sérieux)": "Ton sec, factuel et noir. Dialogues incisifs. Pas d'anachronismes.",
            "Web Novel (Familier)": "Ton fluide et moderne. Phrases courtes. Adapte l'humour pour un public occidental.",
            "Technique / Manuel": "Traduction précise et littérale. Vocabulaire technique cohérent. Ton neutre.",
            "Maintien des suffixe (San, Kun...)": "Conserve les honorifiques japonais (-san, -kun, -sama) dans la traduction."
        }
        
        val = templates.get(text)
        if val:
            current = self.text_edit.toPlainText()
            if current:
                self.text_edit.setPlainText(current + "\n" + val)
            else:
                self.text_edit.setPlainText(val)
                
            self.tpl_combo.setCurrentIndex(0) # Reset combo

    def _save(self):
        self.instructions = self.text_edit.toPlainText().strip()
        self.accept()

    def get_instructions(self):
        return self.instructions
