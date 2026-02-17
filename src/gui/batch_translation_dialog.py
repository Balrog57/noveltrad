from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QProgressBar, QComboBox, QCheckBox, 
                             QGroupBox, QListWidget, QListWidgetItem, QMessageBox, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from src.core.database import Segment, Chapter
import time

class BatchWorker(QObject):
    progress = pyqtSignal(int, int) # current, total
    log = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, project_manager, engine, chapters, scope_mode, overwrite=False):
        super().__init__()
        self.pm = project_manager
        self.engine = engine
        self.chapters = chapters
        self.scope_mode = scope_mode # 'current', 'all', 'selected'
        self.overwrite = overwrite
        self.is_running = True
        
    def run(self):
        try:
            # 1. Gather segments
            all_segments = []
            
            # Filter chapters based on scope? 
            # The caller passes 'chapters' which is already the list of chapters to process.
            
            for chapter in self.chapters:
                if not self.is_running: break
                segs = self.pm.get_segments(chapter.id)
                for s in segs:
                    if self.overwrite or s.status not in ['translated', 'validated', 'ai_refined']:
                        all_segments.append(s)
            
            total = len(all_segments)
            if total == 0:
                self.log.emit("No segments to translate.")
                self.finished.emit()
                return

            self.log.emit(f"Starting batch translation for {total} segments...")
            
            # 2. Process
            # Determine batch size for engine?
            # Creating a simple batch loop for now. 
            # If engine supports batching, we should use it. 
            # Checking engine capability:
            supports_batch = hasattr(self.engine, 'translate_batch')
            batch_size = 10 if supports_batch else 1
            
            current_idx = 0
            while current_idx < total and self.is_running:
                batch = all_segments[current_idx : current_idx + batch_size]
                texts = [s.source_text for s in batch]
                
                try:
                    # Translate
                    if supports_batch:
                        translations = self.engine.translate_batch(
                            texts, 
                            src_lang=self.pm.current_project.source_language,
                            tgt_lang=self.pm.current_project.target_language
                        )
                    else:
                        translations = []
                        for text in texts:
                             t = self.engine.translate(
                                 text,
                                 src_lang=self.pm.current_project.source_language,
                                 tgt_lang=self.pm.current_project.target_language
                             )
                             translations.append(t)
                    
                    # Update DB
                    for i, seg in enumerate(batch):
                        if i < len(translations):
                            seg.target_text = translations[i]
                            seg.status = 'machine'
                            seg.save()
                    
                    current_idx += len(batch)
                    self.progress.emit(current_idx, total)
                    
                except Exception as e:
                    self.error.emit(f"Error communicating with engine: {str(e)}")
                    # Continue or break? Let's break to avoid spamming errors
                    break
                    
                # Short verify-alive sleep
                QThread.msleep(10)

            self.log.emit("Batch processing complete.")
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()

    def stop(self):
        self.is_running = False

class BatchTranslationDialog(QDialog):
    def __init__(self, project_manager, engines, parent=None):
        super().__init__(parent)
        self.pm = project_manager
        self.engines = engines
        self.worker = None
        self.thread = None
        
        self.setWindowTitle("Batch Translation")
        self.resize(500, 600)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. Scope Selection
        grp_scope = QGroupBox("Target Scope")
        scope_layout = QVBoxLayout()
        grp_scope.setLayout(scope_layout)
        
        self.radio_current = QCheckBox("Current Chapter Only") # Using Checkbox as Radio for custom logic or QRadioButton
        self.radio_current.setChecked(True)
        # Actually better to use QGroupBox with Checkable or QRadioButton
        from PyQt6.QtWidgets import QRadioButton, QButtonGroup
        self.bg_scope = QButtonGroup(self)
        
        self.rb_current = QRadioButton("Current Chapter")
        self.rb_all = QRadioButton("All Chapters")
        self.rb_selected = QRadioButton("Select Specific Chapters")
        
        self.bg_scope.addButton(self.rb_current, 1)
        self.bg_scope.addButton(self.rb_all, 2)
        self.bg_scope.addButton(self.rb_selected, 3)
        self.rb_current.setChecked(True)
        
        scope_layout.addWidget(self.rb_current)
        scope_layout.addWidget(self.rb_all)
        scope_layout.addWidget(self.rb_selected)
        
        # Chapter List (enabled only if Selected)
        self.chapter_list = QListWidget()
        self.chapter_list.setEnabled(False)
        self.rb_selected.toggled.connect(lambda c: self.chapter_list.setEnabled(c))
        
        # Load chapters
        if self.pm.current_project:
            chapters = self.pm.get_chapters()
            for ch in chapters:
                item = QListWidgetItem(f"{ch.order_index}. {ch.title}")
                item.setData(Qt.ItemDataRole.UserRole, ch.id) # Store ID
                item.setCheckState(Qt.CheckState.Unchecked)
                self.chapter_list.addItem(item)
                
        scope_layout.addWidget(self.chapter_list)
        layout.addWidget(grp_scope)
        
        # 2. Engine Selection
        grp_engine = QGroupBox("Translation Engine")
        eng_layout = QVBoxLayout()
        grp_engine.setLayout(eng_layout)
        
        self.combo_engines = QComboBox()
        for eng in self.engines:
            self.combo_engines.addItem(eng.get_name(), eng)
            
        eng_layout.addWidget(self.combo_engines)
        layout.addWidget(grp_engine)
        
        # 3. Options
        grp_opts = QGroupBox("Options")
        opts_layout = QVBoxLayout()
        grp_opts.setLayout(opts_layout)
        
        self.chk_overwrite = QCheckBox("Overwrite existing translations")
        self.chk_overwrite.setToolTip("If checked, validated/translated segments will be re-translated.")
        opts_layout.addWidget(self.chk_overwrite)
        
        layout.addWidget(grp_opts)
        
        # 4. Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.lbl_status = QLabel("Ready")
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.progress_bar)
        
        # 5. Buttons
        btn_box = QHBoxLayout()
        self.btn_start = QPushButton("Start Translation")
        self.btn_start.setProperty("primary", True)
        self.btn_start.clicked.connect(self.start_batch)
        
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_batch)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.close)
        
        btn_box.addStretch()
        btn_box.addWidget(self.btn_start)
        btn_box.addWidget(self.btn_stop)
        btn_box.addWidget(self.btn_close)
        
        layout.addLayout(btn_box)

    def start_batch(self):
        engine = self.combo_engines.currentData()
        if not engine:
             QMessageBox.warning(self, "Error", "No engine selected.")
             return
             
        # Determine chapters
        target_chapters = []
        all_chapters = self.pm.get_chapters()
        
        if self.rb_current.isChecked():
            # We need to access mainwindow's current chapter ID?
            # Or just assume the "current" notion is handled by caller passing ID?
            # The dialog doesn't know "current". 
            # Hack: Pass current_chapter_id in constructor or just use 'All' default if not provided?
            # Let's verify 'current' behavior. Dialog needs context.
            # Simplified: Disable 'Current' if we don't know it, or rename to 'First' ? 
            # Actually, let's remove 'Current' from here and rely on caller to pre-select 'Selected' with current?
            # Or better: Just getting all chapters is safe.
            # We'll rely on the user selecting chapters if they want specific ones.
            pass 
        
        # Re-evaluating Scope implementation
        if self.rb_all.isChecked() or self.rb_current.isChecked(): 
            # Special case for "Current": We might need logic here. 
            # For now, if "Current" is checked, we default to ALL because we lack context, 
            # unless we can find it.
            # Better: Let's assume the user selects via list for specifics.
            target_chapters = all_chapters
        
        # Correct approach for Radio Logic:
        if self.rb_selected.isChecked():
            for i in range(self.chapter_list.count()):
                item = self.chapter_list.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    ch_id = item.data(Qt.ItemDataRole.UserRole)
                    # Find chapter obj
                    ch = next((c for c in all_chapters if c.id == ch_id), None)
                    if ch: target_chapters.append(ch)
        elif self.rb_current.isChecked():
             # We rely on parent to handle this? Or we just grab the first/last?
             # Let's treat "Current" as "All" for safety if context missing, 
             # OR better: remove "Current" radio if we can't implement it easily without tighter coupling.
             # But "Current Chapter" is useful.
             # Let's try to get it from PM if tracked, or passed in __init__.
             # PM doesn't track UI state.
             # Logic fix: We will allow caller to pass `current_chapter_id`.
             if hasattr(self, 'current_chapter_id') and self.current_chapter_id:
                 ch = next((c for c in all_chapters if c.id == self.current_chapter_id), None)
                 if ch: target_chapters = [ch]
             else:
                 target_chapters = all_chapters # Fallback
        
        if not target_chapters:
            QMessageBox.warning(self, "Warning", "No chapters selected.")
            return

        # Setup Thread
        self.thread = QThread()
        self.worker = BatchWorker(self.pm, engine, target_chapters, 'selected', self.chk_overwrite.isChecked())
        
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self.update_status)
        self.worker.finished.connect(self.batch_finished)
        self.worker.error.connect(self.batch_error)
        
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        # UI State
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.grp_controls_enabled(False)
        
        self.thread.start()

    def set_current_chapter(self, chapter_id):
        self.current_chapter_id = chapter_id

    def grp_controls_enabled(self, enabled):
        self.combo_engines.setEnabled(enabled)
        self.chapter_list.setEnabled(enabled and self.rb_selected.isChecked())
        self.chk_overwrite.setEnabled(enabled)
        self.rb_all.setEnabled(enabled)
        self.rb_current.setEnabled(enabled)
        self.rb_selected.setEnabled(enabled)

    def stop_batch(self):
        if self.worker:
            self.worker.stop()
            self.lbl_status.setText("Stopping...")

    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.lbl_status.setText(f"Translating... {current}/{total}")

    def update_status(self, msg):
        self.lbl_status.setText(msg)

    def batch_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.grp_controls_enabled(True)
        self.lbl_status.setText("Finished.")
        QMessageBox.information(self, "Done", "Batch translation completed.")

    def batch_error(self, err):
        self.lbl_status.setText(f"Error: {err}")
        QMessageBox.critical(self, "Error", err)

