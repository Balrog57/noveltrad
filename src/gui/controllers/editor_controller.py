from PyQt6.QtCore import Qt, QThread, pyqtSignal
from src.core.database import Segment, Chapter, SegmentStatus
from src.gui.components import SegmentCard

class AutoStructureWorker(QThread):
    progress_update = pyqtSignal(int, str)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, project_manager, llm_engine):
        super().__init__()
        self.project_manager = project_manager
        self.llm_engine = llm_engine

    def run(self):
        try:
            self._emit_progress(10, "Lecture du projet...")
            count = self.project_manager.run_structure_ai(
                self.llm_engine,
                progress_callback=self._emit_progress
            )
            self.finished.emit(count)
        except Exception as e:
            self.error.emit(str(e))

    def _emit_progress(self, val, msg):
        self.progress_update.emit(val, msg)

class EditorController:
    """
    Handles management of chapters, segments, and the editor state.
    Migrated from MainWindow.py.
    """
    def __init__(self, main_window):
        self.main_window = main_window
        self.project_manager = main_window.project_manager

    def load_chapters(self):
        """Loads chapters into the sidebar and updates project name."""
        self.main_window.sidebar.clear()
        if not self.project_manager.current_project:
            return

        chapters = self.project_manager.get_chapters()
        for chapter in chapters:
            total = chapter.segments.count()
            translated = chapter.segments.where(Segment.status != SegmentStatus.UNTRANSLATED.value).count()
            progress = int((translated / total) * 100) if total > 0 else 0
            
            self.main_window.sidebar.add_item(chapter.id, chapter.title, progress)
        
        if self.project_manager.current_project:
            self.main_window.project_name_label.setText(self.project_manager.current_project.name)
            self.main_window.update_footer_stats()

    def select_chapter(self, chapter_id):
        """Callback when a chapter is selected in the sidebar."""
        self.load_segments(chapter_id)

    def load_segments(self, chapter_id=None):
        """Loads segment cards for the given chapter into the scroll area."""
        # Clear existing cards
        while self.main_window.cards_layout.count():
            item = self.main_window.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.project_manager.current_project:
             self.main_window.project_name_label.setText("Aucun Projet Chargé")
             return
             
        self.main_window.project_name_label.setText(self.project_manager.current_project.name)
        
        # If no chapter_id, pick first chapter or restore session
        if not chapter_id:
            chapters = self.project_manager.get_chapters()
            if chapters:
                chapter_id = chapters[0].id
                last_seg_id = None
                
                # Check LastEntryManager to restore session
                if getattr(self.project_manager, 'last_entry', None):
                    for chap in chapters:
                        saved_seg = self.project_manager.last_entry.get_last_segment(chap.title)
                        if saved_seg is not None:
                            chapter_id = chap.id
                            last_seg_id = saved_seg
                            break
                            
                    if last_seg_id is not None:
                        self.main_window.statusBar().showMessage(f"Session restaurée: segment #{last_seg_id}")
                
                self.main_window.sidebar.on_item_clicked(chapter_id)
        
        self.main_window.current_chapter_id = chapter_id

        if chapter_id:
             segments = self.project_manager.get_segments(chapter_id)
             for seg in segments: 
                card = SegmentCard(seg)
                card.set_layout_mode(self.main_window.current_layout_mode)
                card.set_grammar_enabled(self.main_window.realtime_grammar_enabled)
                card.clicked.connect(self.handle_segment_click)
                card.textChanged.connect(self.handle_text_change)
                card.lookupWord.connect(self.main_window.tools_ctrl.on_word_lookup)
                card.forceTranslation.connect(self.handle_force_translation)
                card.machineTranslation.connect(self.handle_machine_translation)
                
                # Check for reference text from tmx2source
                if getattr(self.project_manager, 'tmx2source', None) and self.project_manager.tmx2source.current_mode == "reference_below":
                    ref_text = self.project_manager.tmx2source.get_reference_text(seg.source_text)
                    if ref_text:
                        card.set_reference_text(ref_text)
                        
                self.main_window.cards_layout.addWidget(card)
        
        self.main_window.cards_layout.addStretch()
            
        self.main_window.load_glossary()
        self.main_window.update_footer_stats()
        self.main_window.refresh_preview()

    def handle_segment_click(self, segment_id):
        """Handles single click on a segment card."""
        self.main_window.current_segment_index = segment_id
        
        active_card = None
        for i in range(self.main_window.cards_layout.count() - 1):
            widget = self.main_window.cards_layout.itemAt(i).widget()
            if isinstance(widget, SegmentCard):
                is_active = (widget.segment_id == segment_id)
                widget.set_active(is_active)
                if is_active:
                    active_card = widget
                    
        if active_card:
            self.main_window.statusBar().showMessage(f"Segment {segment_id} sélectionné")
            self.main_window.tools_panel.ai_text.setText("Cliquez sur 'Régénérer Suggestion' pour obtenir une traduction IA.")
            
            # Update last_entry.properties
            if getattr(self.project_manager, 'last_entry', None):
                if active_card.segment.chapter:
                    self.project_manager.last_entry.update_last_segment(active_card.segment.chapter.title, segment_id)
            
            # Auto-Glossary detection
            self.update_glossary_for_segment(active_card.segment.source_text)
            
            # TM searches
            matches = self.project_manager.search_translation_memory(active_card.segment.source_text)
            self.main_window.tools_panel.fuzzy_viewer.set_matches(matches)

    def update_glossary_for_segment(self, text):
        """Find and highlight glossary terms in the given text."""
        self.main_window.glossary_list.clear()
        if not self.project_manager.current_project:
            return
            
        from src.core.database import GlossaryTerm
        project = self.project_manager.current_project
        terms = GlossaryTerm.select().where(GlossaryTerm.project == project)
        
        found = 0
        for term in terms:
            if term.source_term.lower() in text.lower():
                item = QListWidgetItem(f"{term.source_term} → {term.target_term}")
                if term.is_auto_generated:
                    item.setForeground(Qt.GlobalColor.gray)
                self.main_window.glossary_list.addItem(item)
                found += 1
                
        if found == 0:
            self.main_window.glossary_list.addItem("Aucune correspondance pour ce segment.")

    def handle_text_change(self, segment_id, new_text):
        """Auto-save segment text changes and update progress."""
        try:
            segment = Segment.get_by_id(segment_id)
            segment.target_text = new_text
            if not segment.status or segment.status == SegmentStatus.UNTRANSLATED.value:
                 if new_text.strip():
                     segment.set_status(SegmentStatus.VALIDATED)
            segment.save()
            
            # Update UI elements that depend on progress
            self.main_window.update_footer_stats()
            self.main_window.update_current_chapter_progress()
            self.main_window.refresh_preview()
        except Exception:
            pass

    def save_active_segment(self):
        """Explicitly save current segment (Ctrl+S)."""
        if self.main_window.current_segment_index == -1:
            return
        for i in range(self.main_window.cards_layout.count() - 1):
            widget = self.main_window.cards_layout.itemAt(i).widget()
            if isinstance(widget, SegmentCard) and widget.segment_id == self.main_window.current_segment_index:
                text = widget.target_edit.toPlainText()
                widget.segment.target_text = text
                if text:
                    widget.segment.set_status(SegmentStatus.VALIDATED)
                    self.project_manager.add_to_tm(widget.segment.source_text, text)
                widget.segment.save()
                self.main_window.statusBar().showMessage(f"Segment {self.main_window.current_segment_index} validé et enregistré.")
                self.main_window.update_footer_stats()
                self.main_window.update_current_chapter_progress()
                self.main_window.refresh_preview()
                break

    def undo(self):
        """Trigger undo on the active segment."""
        if self.main_window.current_segment_index == -1: return
        for i in range(self.main_window.cards_layout.count() - 1):
            widget = self.main_window.cards_layout.itemAt(i).widget()
            if isinstance(widget, SegmentCard) and widget.segment_id == self.main_window.current_segment_index:
                widget.target_edit.undo()
                break

    def redo(self):
        """Trigger redo on the active segment."""
        if self.main_window.current_segment_index == -1: return
        for i in range(self.main_window.cards_layout.count() - 1):
            widget = self.main_window.cards_layout.itemAt(i).widget()
            if isinstance(widget, SegmentCard) and widget.segment_id == self.main_window.current_segment_index:
                widget.target_edit.redo()
                break

    def apply_translation_match(self, match_data):
        """Apply a fuzzy translation match to the active segment."""
        if self.main_window.current_segment_index == -1:
            return
            
        target_text = match_data.get('target', '')
        if not target_text:
            return
            
        for i in range(self.main_window.cards_layout.count() - 1):
            widget = self.main_window.cards_layout.itemAt(i).widget()
            if isinstance(widget, SegmentCard) and widget.segment_id == self.main_window.current_segment_index:
                widget.target_edit.setPlainText(target_text)
                self.save_active_segment()
                self.main_window.statusBar().showMessage("Traduction de la mémoire sélectionnée et sauvegardée.", 3000)
                break

    def handle_force_translation(self, segment_id):
        segment = Segment.get_by_id(segment_id)
        enforce_match = self.project_manager.enforce_tm.enforce_translation(segment.source_text)
        if enforce_match:
             self.project_manager.enforce_tm.force_replace(segment, enforce_match)
             for i in range(self.main_window.cards_layout.count() - 1):
                 widget = self.main_window.cards_layout.itemAt(i).widget()
                 if isinstance(widget, SegmentCard) and widget.segment_id == segment_id:
                     widget.target_edit.setPlainText(enforce_match)
                     widget.update_status_style()
                     break
             self.main_window.statusBar().showMessage(f"Segment {segment_id} forcé depuis TM Enforce.")
        else:
             self.main_window.statusBar().showMessage(f"Aucune correspondance Enforce TM pour ce segment.", 3000)

    def handle_machine_translation(self, segment_id):
        segment = Segment.get_by_id(segment_id)
        suggestions = self.project_manager.mt_manager.get_mt_suggestions(segment.source_text)
        if suggestions:
             best_match = suggestions[0]
             self.project_manager.mt_manager.mark_as_mt(segment, best_match)
             for i in range(self.main_window.cards_layout.count() - 1):
                 widget = self.main_window.cards_layout.itemAt(i).widget()
                 if isinstance(widget, SegmentCard) and widget.segment_id == segment_id:
                     widget.target_edit.setPlainText(best_match['target'])
                     widget.status_badge.setText(f"MT: {best_match['score']}%")
                     widget.status_badge.setStyleSheet("font-size: 9px; font-weight: 800; color: #ff6b6b; border: 1px solid #ff6b6b; padding: 2px 6px; border-radius: 4px;")
                     widget.setStyleSheet(widget.styleSheet() + " QFrame#SegmentCard { border-left: 4px solid #ff6b6b; }")
                     break
             self.main_window.statusBar().showMessage(f"Suggestion Machine appliquée (Score: {best_match['score']}%).")
        else:
             self.main_window.statusBar().showMessage("Aucune suggestion Machine Translation trouvée.", 3000)

    def auto_translate_current(self):
        """Translate the active segment using the current AI engine."""
        if self.main_window.current_segment_index == -1: return
        
        active_card = None
        for i in range(self.main_window.cards_layout.count() - 1):
            widget = self.main_window.cards_layout.itemAt(i).widget()
            if isinstance(widget, SegmentCard) and widget.segment_id == self.main_window.current_segment_index:
                active_card = widget
                break
                
        if not active_card: return
        
        try:
            self.main_window.statusBar().showMessage("Génération de la suggestion IA...")
            QApplication.processEvents()
            
            p = self.project_manager.current_project
            src = active_card.segment.source_text
            
            # Get glossary terms
            from src.core.database import GlossaryTerm
            glossary_terms = {}
            for term in GlossaryTerm.select().where(GlossaryTerm.project == p):
                glossary_terms[term.source_term] = term.target_term
            
            engine = self.main_window.get_current_translation_engine()
            trans = engine.translate(
                src, p.source_language, p.target_language,
                glossary_terms=glossary_terms,
                genre=p.genre,
                custom_instructions=p.custom_instructions
            )
            
            active_card.target_edit.setPlainText(trans)
            self.main_window.tools_panel.ai_text.setText(trans)
            
            active_card.segment.target_text = trans
            active_card.segment.set_status(SegmentStatus.VALIDATED)
            active_card.segment.save()
            
            self.main_window.statusBar().showMessage("Traduit et Sauvegardé.")
        except Exception as e:
            self.main_window.tools_panel.ai_text.setText(f"Erreur : {e}")

    def add_glossary_term(self):
        """Opens dialog to add a new glossary term manually."""
        if not self.project_manager.current_project: return
        
        from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QHBoxLayout, QPushButton
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("Ajouter un Terme")
        layout = QFormLayout(dialog)
        
        src_input = QLineEdit()
        tgt_input = QLineEdit()
        layout.addRow("Source :", src_input)
        layout.addRow("Cible :", tgt_input)
        
        btns = QHBoxLayout()
        ok_btn = QPushButton("Ajouter")
        ok_btn.clicked.connect(dialog.accept)
        btns.addWidget(ok_btn)
        layout.addRow(btns)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            src = src_input.text().strip()
            tgt = tgt_input.text().strip()
            if src and tgt:
                from src.core.database import GlossaryTerm
                GlossaryTerm.create(
                    project=self.project_manager.current_project,
                    source_term=src,
                    target_term=tgt,
                    is_auto_generated=False
                )
                self.load_glossary()

    def load_glossary(self):
        """Refreshes the glossary list in the tools panel."""
        self.main_window.glossary_list.clear()
        if not self.project_manager.current_project: return
        
        from src.core.database import GlossaryTerm
        terms = GlossaryTerm.select().where(GlossaryTerm.project == self.project_manager.current_project)
        for term in terms:
           item = QListWidgetItem(f"{term.source_term} -> {term.target_term}")
           self.main_window.glossary_list.addItem(item)
           
    def run_structure_ai(self):
        """Run Structure AI to auto-detect chapters using a background worker."""
        if not self.project_manager.current_project:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self.main_window, "Erreur", "Aucun projet chargé.")
            return

        from PyQt6.QtWidgets import QMessageBox
        if not self.main_window.llm_engine or not self.main_window.llm_engine.is_available():
            QMessageBox.warning(self.main_window, "Erreur", "Moteur IA non disponible. Vérifiez les paramètres.")
            return

        reply = QMessageBox.question(
            self.main_window, "Structure Auto du Projet",
            "Les chapitres existants seront écrasés. Voulez-vous continuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return

        from PyQt6.QtWidgets import QProgressDialog
        self.progress_dialog = QProgressDialog("Analyse de la structure...", "Annuler", 0, 100, self.main_window)
        self.progress_dialog.setWindowTitle("Structure AI")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setCancelButton(None)
        
        self.structure_worker = AutoStructureWorker(self.project_manager, self.main_window.llm_engine)
        self.structure_worker.progress_update.connect(self._on_structure_progress)
        self.structure_worker.finished.connect(self._on_structure_finished)
        self.structure_worker.error.connect(self._on_structure_error)
        
        self.structure_worker.start()
        
    def _on_structure_progress(self, val, msg):
        self.progress_dialog.setValue(val)
        self.progress_dialog.setLabelText(msg)
        
    def _on_structure_finished(self, count):
        self.progress_dialog.close()
        if count > 0:
            self.load_chapters()
            self.load_segments()
            self.main_window.statusBar().showMessage(f"Structure AI : {count} chapitres créés.")

    def _on_structure_error(self, err_msg):
        self.progress_dialog.close()
    def set_source_tooltips(self, text):
        """Sets the tooltip for all source edit fields in the cards layout."""
        for i in range(self.main_window.cards_layout.count() - 1):
            widget = self.main_window.cards_layout.itemAt(i).widget()
            if isinstance(widget, SegmentCard):
                widget.source_edit.setToolTip(text)

    def toggle_reference_mode(self, checked):
        """Toggles the display of the 3rd language reference."""
        if getattr(self.project_manager, 'tmx2source', None):
            self.project_manager.tmx2source.display_mode("reference_below" if checked else "normal")
            if getattr(self.main_window, 'current_chapter_id', None):
                self.load_segments(self.main_window.current_chapter_id)
