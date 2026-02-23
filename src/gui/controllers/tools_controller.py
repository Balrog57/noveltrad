from PyQt6.QtWidgets import QFileDialog, QMessageBox, QListWidgetItem, QInputDialog
from src.core.database import GlossaryTerm, Segment
from src.core.dictionary_manager import DictionaryManager
from src.core.concordancer import Concordancer
from src.gui.glossary_editor_dialog import GlossaryEditorDialog
from src.gui.qa_dialog import QADialog
from src.gui.alignment_dialog import AlignmentDialog

class ToolsController:
    def __init__(self, main_window):
        self.main_window = main_window
        self.project_manager = main_window.project_manager

    def search_dictionary(self):
        """Search the dictionary for the terms entered in the Tools Panel."""
        query = self.main_window.dict_input.text().strip()
        if not query:
            return
            
        src_lang = self.main_window.source_lang_combo.currentText()
        tgt_lang = self.main_window.target_lang_combo.currentText()
        
        self.main_window.dict_results.setText("Recherche...")
        results = DictionaryManager.search_term(query, src_lang, tgt_lang)
        
        if not results:
            self.main_window.dict_results.setText("Aucun résultat.")
            return
            
        # Format results for the label
        formatted = ""
        for r in results[:3]: # Limit to top 3 for the small label
            formatted += f"• <b>{r['source_term']}</b> ➔ {r['target_term']}<br>"
            if r.get('context'):
                formatted += f"  <i><small>({r['context']})</small></i><br>"
        
        self.main_window.dict_results.setText(formatted)
        self.main_window.statusBar().showMessage(f"Dictionnaire : {len(results)} entrée(s) trouvée(s).", 3000)

    def on_word_lookup(self, word):
        """Handle word lookup from hover tooltip."""
        src_lang = self.main_window.source_lang_combo.currentText()
        tgt_lang = self.main_window.target_lang_combo.currentText()
        
        dm = DictionaryManager()
        results = dm.search(src_lang, tgt_lang, word)
        
        if results:
            result = results[0]
            tooltip_text = f"{result.source_term} → {result.target_term}"
            if result.context:
                tooltip_text += f"\n[{result.context}]"
            
            # Use editor_ctrl to set tooltips
            if hasattr(self.main_window, 'editor_ctrl'):
                self.main_window.editor_ctrl.set_source_tooltips(tooltip_text)
        else:
            if hasattr(self.main_window, 'editor_ctrl'):
                self.main_window.editor_ctrl.set_source_tooltips("")

    def search_concordancer(self):
        """Global search in project segments and TM."""
        query = self.main_window.conc_input.text().strip()
        if not query:
            return
            
        self.main_window.conc_results.clear()
        self.main_window.conc_results.addItem("Recherche en cours...")
        
        concordancer = Concordancer()
        segments = list(self.project_manager.get_segments()) if self.project_manager.current_project else []
        results = concordancer.search(query, segments=segments, tm_entries=[])
        
        self.main_window.conc_results.clear()
        if results:
            for r in results:
                # Truncate for display
                source = (r.source_text[:50] + '..') if len(r.source_text) > 50 else r.source_text
                target = (r.target_text[:50] + '..') if r.target_text and len(r.target_text) > 50 else (r.target_text or "---")
                
                text = f"[{r.match_type}] {source}\n➔ {target}"
                item = QListWidgetItem(text)
                self.main_window.conc_results.addItem(item)
        else:
            self.main_window.conc_results.addItem("Aucun résultat trouvé.")

    def open_glossary_manager(self):
        """Open the comprehensive glossary editor."""
        if not self.project_manager.current_project:
            QMessageBox.warning(self.main_window, "Glossaire", "Ouvrez un projet pour gérer le glossaire.")
            return
        
        dialog = GlossaryEditorDialog(self.main_window, self.project_manager.current_project)
        dialog.exec()
        # Refresh current view glossary list
        if hasattr(self.main_window, 'editor_ctrl'):
            self.main_window.editor_ctrl.load_glossary()

    def run_qa_check(self):
        """Open the Quality Assurance dialog."""
        if not self.project_manager.current_project:
            QMessageBox.warning(self.main_window, "QA", "Aucun projet ouvert.")
            return

        segments = list(self.project_manager.get_segments())
        glossary_terms = list(
            GlossaryTerm.select().where(
                GlossaryTerm.project == self.project_manager.current_project
            )
        )

        dialog = QADialog(self.main_window, segments=segments, glossary_terms=glossary_terms)
        # Re-connect navigation if editor_ctrl exists
        if hasattr(self.main_window, 'editor_ctrl'):
            dialog.navigate_to_segment.connect(self.main_window.editor_ctrl.on_segment_card_clicked)
        dialog.exec()

    def open_alignment_tool(self):
        """Open the alignment tool."""
        dialog = AlignmentDialog(self.main_window, project_manager=self.project_manager)
        dialog.exec()

    def show_search_replace(self):
        """Open the Search and Replace dialog."""
        if not self.project_manager.current_project:
            QMessageBox.warning(self.main_window, "Erreur", "Veuillez d'abord ouvrir un projet.")
            return
            
        from src.gui.search_replace_dialog import SearchReplaceDialog
        dialog = SearchReplaceDialog(self.main_window, self.project_manager)
        dialog.show() # Non-modal to allow interacting with the main window

    def import_dictionary(self):
        """Import dictionary from JSON file"""
        from PyQt6.QtWidgets import QFileDialog
        fname, _ = QFileDialog.getOpenFileName(
            self.main_window, "Importer Dictionnaire", "", 
            "Fichiers Dictionnaire (*.json);;Tous les fichiers (*)"
        )
        if not fname:
            return
            
        src_lang = self.main_window.source_lang_combo.currentText()
        tgt_lang = self.main_window.target_lang_combo.currentText()
        
        count = DictionaryManager.import_from_json(fname, src_lang, tgt_lang)
        QMessageBox.information(self.main_window, "Import Terminé", f"Importé {count} termes.")
        self.main_window.statusBar().showMessage(f"Import du dictionnaire terminé : {count} termes.", 3000)

    def show_statistics(self):
        """Show project statistics dialog."""
        if not self.project_manager.current_project:
            QMessageBox.warning(self.main_window, "Statistiques", "Aucun projet ouvert.")
            return
        from src.gui.statistics_dialog import StatisticsDialog
        dialog = StatisticsDialog(self.project_manager.current_project, self.main_window)
        dialog.exec()
