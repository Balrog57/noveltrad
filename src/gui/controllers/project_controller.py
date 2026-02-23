import os
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QApplication
from src.core.project_manager import ProjectManager
from src.core.backup_manager import BackupManager
from src.gui.new_project_dialog import NewProjectDialog

class ProjectController:
    def __init__(self, main_window):
        self.main_window = main_window
        self.project_manager = main_window.project_manager
        
    def new_project(self):
        dialog = NewProjectDialog(self.main_window, self.main_window.language_manager)
        if dialog.exec():
            data = dialog.get_data()
            db_path, _ = QFileDialog.getSaveFileName(
                self.main_window, "Save Project File", 
                os.path.join(os.getcwd(), f"{data['name']}.ntrad"),
                "NovelTrad Project (*.ntrad)"
            )
            
            if db_path:
                try:
                    self.main_window.statusBar().showMessage("Creating project...")
                    QApplication.processEvents()
                    
                    self.project_manager.create_project(
                        name=data['name'],
                        db_path=db_path,
                        source_file=data['source_path'],
                        source_lang=data['source_lang'],
                        target_lang=data['target_lang']
                    )
                    self.load_project(db_path)
                    QMessageBox.information(self.main_window, "Success", "Project created successfully!")
                except Exception as e:
                    QMessageBox.critical(self.main_window, "Error", f"Failed to create project: {e}")

    def load_project(self, fname=None):
        if not fname:
            fname, _ = QFileDialog.getOpenFileName(self.main_window, "Open Project", "", "NovelTrad Projects (*.ntrad)")
        
        if fname:
            try:
                self.project_manager.load_project(fname)
                self.main_window.backup_manager = BackupManager(fname)
                self.main_window.backup_manager.create_snapshot(label="load")
                
                self.main_window.load_chapters()
                self.main_window.load_segments()
                self.main_window.statusBar().showMessage(f"Loaded project: {fname}")
                self.main_window.update_project_ui()
            except Exception as e:
                QMessageBox.critical(self.main_window, "Error", f"Failed to open project: {str(e)}")

    def import_chapter(self):
        if not self.project_manager.current_project:
            QMessageBox.warning(self.main_window, "Error", "No project loaded.")
            return

        fname, _ = QFileDialog.getOpenFileName(
            self.main_window, "Import Chapter", "", 
            "Documents (*.txt *.docx *.epub *.pdf);;All Files (*)"
        )
        
        if fname:
            try:
                self.project_manager.import_file(fname)
                self.main_window.load_chapters()
                self.main_window.statusBar().showMessage(f"Imported chapter: {os.path.basename(fname)}")
            except Exception as e:
                 QMessageBox.critical(self.main_window, "Error", f"Failed to import chapter: {str(e)}")

    def export_project(self):
        if not self.project_manager.current_project:
            QMessageBox.warning(self.main_window, "Erreur", "Aucun projet actif à exporter.")
            return
            
        source_path = self.project_manager.current_project.file_path
        _, ext = os.path.splitext(source_path)
        
        filters = f"Format Original (*{ext});;Fichier PDF (*.pdf)"
        if ext.lower() == ".pdf":
            filters = "Fichier PDF (*.pdf)"
            
        fname, selected_filter = QFileDialog.getSaveFileName(self.main_window, "Exporter Fichier Traduit", f"translated_output{ext}", filters)
        
        if fname:
            if "PDF" in selected_filter and not fname.lower().endswith(".pdf"):
                fname = os.path.splitext(fname)[0] + ".pdf"
            elif "Original" in selected_filter and not fname.lower().endswith(ext.lower()):
                fname = os.path.splitext(fname)[0] + ext
                
            try:
                self.main_window.statusBar().showMessage(f"Export vers {fname}...")
                QApplication.processEvents()
                self.project_manager.export_project(fname)
                self.main_window.statusBar().showMessage("Export terminé.")
                QMessageBox.information(self.main_window, "Succès", "Fichier exporté avec succès.")
            except Exception as e:
                QMessageBox.critical(self.main_window, "Erreur", f"Échec de l'export : {str(e)}")

    def show_statistics(self):
        if not self.project_manager.current_project:
            QMessageBox.warning(self.main_window, "Erreur", "Aucun projet actif.")
            return
        
        from src.gui.stats_dialog import StatsDialog
        dialog = StatsDialog(self.main_window, self.project_manager)
        dialog.exec()

    def show_backup_dialog(self):
        if not self.main_window.backup_manager:
            QMessageBox.warning(self.main_window, "Erreur", "Aucun projet chargé.")
            return
            
        from src.gui.backup_dialog import BackupDialog
        dialog = BackupDialog(self.main_window, self.main_window.backup_manager)
        if dialog.exec():
            # If a backup was restored, we need to reload
            self.load_project(self.main_window.backup_manager.db_path)
