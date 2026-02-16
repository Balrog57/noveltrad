import os
import sys

# Add project root to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

# Fix DLL Loading Errors: onnxruntime and ctranslate2 must be imported before PyQt6
# to avoid conflicts with Qt's bundled DLLs (e.g. msvcp140 or zlib)
try:
    import onnxruntime
except ImportError:
    pass

try:
    import ctranslate2
except ImportError:
    pass

from PyQt6.QtWidgets import QApplication
from src.gui.mainwindow import MainWindow
from src.core.config_manager import ConfigManager
from src.gui.first_run_wizard import FirstRunWizard

def main():
    app = QApplication(sys.argv)
    
    config = ConfigManager()
    if config.is_first_run():
        wizard = FirstRunWizard()
        if not wizard.exec():
            sys.exit(0) # User cancelled
            
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
