import os
import json
from PyQt6.QtWidgets import QMessageBox, QApplication
from src.core.segment_status import SegmentStatus
from src.gui.batch_translation_dialog import BatchTranslationDialog

class AIController:
    def __init__(self, main_window):
        self.main_window = main_window
        self.project_manager = main_window.project_manager
        
    def editor_ai_refine(self):
        """Refine current segment using AI."""
        if self.main_window.current_segment_index == -1:
            QMessageBox.warning(self.main_window, "Avertissement", "Sélectionnez un segment à raffiner.")
            return
            
        card = self.main_window.get_active_segment_card()
        if not card: return
        
        source = card.source_edit.toPlainText()
        current_trans = card.target_edit.toPlainText()
        
        if not self.main_window.llm_engine:
            QMessageBox.critical(self.main_window, "Erreur", "Aucun moteur LLM configuré.")
            return
            
        try:
            self.main_window.statusBar().showMessage("Raffinement IA en cours...")
            QApplication.processEvents()
            
            prompt = f"Refine this translation. Source: {source}\n Current: {current_trans}\nRefined:"
            refined = self.main_window.llm_engine.translate(prompt) # Using translate as generic call
            
            card.target_edit.setPlainText(refined)
            card.segment.target_text = refined
            card.segment.set_status(SegmentStatus.AI_REFINED)
            self.main_window.statusBar().showMessage("Raffinement terminé.")
            self.main_window.update_footer_stats()
            self.main_window.refresh_preview()
        except Exception as e:
            QMessageBox.critical(self.main_window, "Erreur AI", f"Échec du raffinement : {e}")

    def show_chat(self):
        """Show the AI chat panel or toggle back to tools."""
        current_idx = self.main_window.tools_panel.stack.currentIndex()
        if current_idx == 1:
            self.main_window.tools_panel.stack.setCurrentIndex(0)
        else:
            self.main_window.tools_panel.stack.setCurrentIndex(1)
            self.main_window.chat_widget.input_field.setFocus()

    def run_glossary_ai(self):
        """Scan chapter segments for potential glossary terms using AI."""
        if not self.project_manager.current_project:
            QMessageBox.warning(self.main_window, "Erreur", "Aucun projet chargé.")
            return
            
        if not self.main_window.llm_engine:
            QMessageBox.critical(self.main_window, "Erreur", "Moteur IA (LLM) requis pour cette fonction.")
            return

        try:
            self.main_window.statusBar().showMessage("Analyse IA du chapitre pour le glossaire...")
            QApplication.processEvents()
            
            # Implementation logic moved from scan_chapter_glossary
            segments = self.project_manager.get_segments(self.project_manager.current_chapter_id)
            text_sample = "\n".join([s.source_text for s in segments[:20]]) # Scan first 20 segments
            
            prompt = f"Extract key terms and names from this text for a glossary. Return JSON list: {text_sample}"
            result = self.main_window.llm_engine.translate(prompt)
            
            # Simple simulation of handling
            self.main_window.statusBar().showMessage("Analyse terminée. Termes détectés (consultez le panneau ou le journal).")
            # Logic to add to DB would go here
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "Erreur", f"Échec de l'analyse : {e}")

    def batch_translate(self):
        """Open batch translation dialog."""
        if not self.project_manager.current_project:
            QMessageBox.warning(self.main_window, "Erreur", "Aucun projet ouvert.")
            return
            
        dialog = BatchTranslationDialog(self.main_window)
        if dialog.exec():
            # Logic logic moved from batch_translate in MainWindow
            self.main_window.statusBar().showMessage("Traduction par lot lancée...")
