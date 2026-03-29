from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLabel, QLineEdit, QPushButton, QCheckBox, QMessageBox)
from src.gui.components import SegmentCard
import re

class SearchReplaceDialog(QDialog):
    def __init__(self, main_window, project_manager):
        super().__init__(main_window)
        self.main_window = main_window
        self.project_manager = project_manager
        self.last_match_index = -1
        
        self.setWindowTitle("Rechercher et Remplacer")
        self.resize(500, 200)
        self._init_ui()
        
    def _init_ui(self):
        layout = QFormLayout(self)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Texte à rechercher...")
        self.search_input.textChanged.connect(self._reset_search)
        
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Remplacer par...")
        
        self.use_regex = QCheckBox("Utiliser les expressions régulières")
        self.case_sensitive = QCheckBox("Respecter la casse")
        self.case_sensitive.setChecked(True)
        
        self.search_source = QCheckBox("Rechercher dans le texte Source (Lecture seule)")
        
        layout.addRow("Rechercher :", self.search_input)
        layout.addRow("Remplacer par :", self.replace_input)
        layout.addRow(self.use_regex)
        layout.addRow(self.case_sensitive)
        layout.addRow(self.search_source)
        
        buttons = QHBoxLayout()
        
        find_btn = QPushButton("Rechercher le suivant")
        find_btn.clicked.connect(self._find_text)
        
        replace_btn = QPushButton("Remplacer")
        replace_btn.clicked.connect(self._replace_text)
        
        replace_all_btn = QPushButton("Remplacer tout")
        replace_all_btn.clicked.connect(self._replace_all_text)
        
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.accept)
        
        buttons.addWidget(find_btn)
        buttons.addWidget(replace_btn)
        buttons.addWidget(replace_all_btn)
        buttons.addWidget(close_btn)
        
        layout.addRow(buttons)

    def _reset_search(self):
        self.last_match_index = -1

    def _get_pattern(self):
        search_text = self.search_input.text()
        if not search_text:
            return None
            
        pattern_flags = 0 if self.case_sensitive.isChecked() else re.IGNORECASE
        
        try:
            if self.use_regex.isChecked():
                return re.compile(search_text, pattern_flags)
            else:
                return re.compile(re.escape(search_text), pattern_flags)
        except re.error as e:
            QMessageBox.warning(self, "Erreur Regex", f"Expression régulière invalide : {str(e)}")
            return None

    def _find_text(self):
        pattern = self._get_pattern()
        if not pattern:
            return
            
        segments = self.project_manager.get_segments()
        
        start_idx = self.last_match_index + 1
        
        for i in range(start_idx, len(segments)):
            seg = segments[i]
            text_to_search = seg.source_text if self.search_source.isChecked() else seg.target_text
            
            if text_to_search and pattern.search(text_to_search):
                self.last_match_index = i
                self._highlight_segment(seg)
                self.main_window.statusBar().showMessage(f"Trouvé au segment {seg.index+1}")
                return
                
        # If we reach here, we didn't find anything or we wrapped around
        if self.last_match_index >= 0:
            QMessageBox.information(self, "Fin", "Recherche terminée (fin du document).")
            self.last_match_index = -1
        else:
            QMessageBox.information(self, "Non trouvé", "Aucune correspondance trouvée.")

    def _highlight_segment(self, segment):
        # Tell main window to load the chapter and focus the segment
        self.main_window.load_segments(segment.chapter_id)
        self.main_window.editor_ctrl.on_segment_card_clicked(segment.id)

        card = self.main_window.get_active_segment_card()
        if not card:
            return

        if self.search_source.isChecked():
            card.source_edit.setFocus()
        else:
            card.target_edit.setFocus()

    def _replace_text(self):
        if self.search_source.isChecked():
            QMessageBox.warning(self, "Lecture seule", "Impossible de remplacer dans le texte source.")
            return
            
        pattern = self._get_pattern()
        if not pattern:
            return
            
        replace_text = self.replace_input.text()
        
        # Replace ONLY on the currently focused segment if it matches, to mimic "Replace" behavior
        if self.last_match_index >= 0:
            segments = self.project_manager.get_segments()
            if self.last_match_index < len(segments):
                seg = segments[self.last_match_index]
                if seg.target_text and pattern.search(seg.target_text):
                    new_text = pattern.sub(replace_text, seg.target_text, count=1)
                    if new_text != seg.target_text:
                        seg.target_text = new_text
                        seg.save()
                        self.main_window.statusBar().showMessage(f"Remplacé au segment {seg.index+1}")
                        self._highlight_segment(seg) # Refresh UI
                        
                        # Find next
                        self._find_text()
                        return
                        
        # If we haven't found anything to replace yet, find first
        self._find_text()

    def _replace_all_text(self):
        if self.search_source.isChecked():
            QMessageBox.warning(self, "Lecture seule", "Impossible de remplacer dans le texte source.")
            return
            
        pattern = self._get_pattern()
        if not pattern:
            return
            
        replace_text = self.replace_input.text()
        segments = self.project_manager.get_segments()
        
        count = 0
        mod_segments = 0
        
        for seg in segments:
            if seg.target_text:
                new_text, subs = pattern.subn(replace_text, seg.target_text)
                if subs > 0:
                    seg.target_text = new_text
                    seg.save()
                    count += subs
                    mod_segments += 1
                    
        if count > 0:
            QMessageBox.information(self, "Succès", f"Remplacé {count} occurrence(s) dans {mod_segments} segment(s).")
            # Refresh current view
            chapter_id = self.main_window.current_chapter_id
            if chapter_id:
                self.main_window.load_segments(chapter_id)
        else:
            QMessageBox.information(self, "Non trouvé", "Aucune correspondance à remplacer.")
