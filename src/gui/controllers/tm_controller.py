from PyQt6.QtWidgets import QFileDialog, QMessageBox, QListWidgetItem
from src.core.concordancer import Concordancer

class TMController:
    def __init__(self, main_window):
        self.main_window = main_window
        self.project_manager = main_window.project_manager
        
    def import_global_tmx(self):
        file_path, _ = QFileDialog.getOpenFileName(self.main_window, "Importer Mémoire TMX Globale", "", "TMX files (*.tmx)")
        if file_path:
            count = self.project_manager.import_tm(file_path)
            QMessageBox.information(self.main_window, "Import TMX", f"{count} segments importés dans la mémoire globale.")

    def export_global_tmx(self):
        file_path, _ = QFileDialog.getSaveFileName(self.main_window, "Exporter Mémoire TMX Globale", "", "TMX files (*.tmx)")
        if file_path:
            self.project_manager.export_tm(file_path)
            QMessageBox.information(self.main_window, "Export TMX", "Mémoire globale exportée avec succès.")

    def import_project_tmx(self):
        if not self.project_manager.current_project:
            QMessageBox.warning(self.main_window, "Erreur", "Ouvrez un projet avant d'importer une mémoire.")
            return
        fname, _ = QFileDialog.getOpenFileName(self.main_window, "Importer TMX dans le Projet", "", "TMX files (*.tmx)")
        if fname:
            try:
                count = self.project_manager.import_project_tmx(fname)
                self.main_window.load_segments()
                QMessageBox.information(self.main_window, "Succès", f"TMX importé : {count} segments mis à jour dans le projet.")
            except Exception as e:
                QMessageBox.critical(self.main_window, "Erreur", f"Échec Import Projet TMX : {e}")

    def export_project_tmx(self):
        if not self.project_manager.current_project: return
        fname, _ = QFileDialog.getSaveFileName(self.main_window, "Exporter Projet en TMX", "project_translations.tmx", "TMX files (*.tmx)")
        if fname:
            try:
                if self.project_manager.export_project_tmx(fname):
                    QMessageBox.information(self.main_window, "Succès", "Projet exporté en TMX avec succès.")
                else:
                    QMessageBox.critical(self.main_window, "Erreur", "Échec de l'export TMX.")
            except Exception as e:
                QMessageBox.critical(self.main_window, "Erreur", f"Échec Export TMX : {e}")

    def search_concordancer(self):
        query = self.main_window.conc_input.text().strip()
        if not query: return
        self.main_window.conc_results.clear()
        concordancer = Concordancer()
        segments = list(self.project_manager.get_segments()) if self.project_manager.current_project else []
        results = concordancer.search(query, segments=segments, tm_entries=[])
        if results:
            for r in results:
                text = f"[{r.match_type}] {r.source_text[:60]}..."
                if r.target_text: text += f"\n→ {r.target_text[:60]}..."
                self.main_window.conc_results.addItem(QListWidgetItem(text))
        else:
            self.main_window.conc_results.addItem("Aucun résultat trouvé.")
