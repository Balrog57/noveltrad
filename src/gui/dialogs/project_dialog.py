"""ProjectDialog — minimal create-project form (name + folder)."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from src.gui.a11y import configure


class ProjectDialog(QDialog):
    """Minimal dialog: project name + working folder."""

    def __init__(
        self,
        parent=None,
        title: str = "New Project",
        initial_name: str = "",
        initial_folder: str = "",
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(480, 180)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Name.
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel(self.tr("Nom:")))
        self._name = QLineEdit(initial_name)
        self._name.setPlaceholderText(self.tr("Ex: Renegade Immortal"))
        configure(self._name, name=self.tr("Project Name"), description=self.tr("Enter the name of the new project."))
        name_row.addWidget(self._name)
        layout.addLayout(name_row)

        # Folder.
        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel(self.tr("Dossier:")))
        self._folder = QLineEdit(initial_folder)
        self._folder.setPlaceholderText(self.tr("C:\\Novels\\Renegade\\"))
        configure(self._folder, name=self.tr("Project Folder"), description=self.tr("Enter the path for the project working directory."))
        folder_row.addWidget(self._folder)
        browse_btn = QPushButton(self.tr("📂"))
        browse_btn.setFixedWidth(36)
        browse_btn.clicked.connect(self._browse)
        configure(
            browse_btn,
            name=self.tr("Browse Folders"),
            tooltip=self.tr("Open a dialog to choose the working folder.")
        )
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        # Hint.
        hint = QLabel(
            self.tr(
                "Le dossier sert de répertoire de travail : "
                "traductions, glossaires et fichiers de sortie."
            )
        )
        hint.setWordWrap(True)
        hint.setProperty("role", "muted")
        layout.addWidget(hint)

        layout.addStretch(1)

        # Buttons.
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(self.tr("Créer"))
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._name.setFocus()

    def project_name(self) -> str:
        return self._name.text().strip()

    def project_folder(self) -> str:
        return self._folder.text().strip()

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            self.tr("Choisir le dossier de travail"),
            str(Path.home() / "Documents"),
        )
        if folder:
            self._folder.setText(folder)
            # Auto-fill name from folder if empty.
            if not self._name.text().strip():
                self._name.setText(Path(folder).name)

    def _validate_and_accept(self) -> None:
        if not self.project_name():
            self._name.setFocus()
            return
        if not self.project_folder():
            self._folder.setFocus()
            return
        self.accept()


__all__ = ["ProjectDialog"]
