import os
import sys

# Add project root to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

# Fix DLL Loading Errors: onnxruntime and ctranslate2 must be imported before PyQt6
# to avoid conflicts with Qt's bundled DLLs (e.g. msvcp140 or zlib)
try:
    import onnxruntime  # noqa: F401
except ImportError:
    pass

try:
    import ctranslate2  # noqa: F401
except ImportError:
    pass

ARGOS_AVAILABLE = False
try:
    import argostranslate.package  # noqa: F401
    import argostranslate.translate  # noqa: F401
    ARGOS_AVAILABLE = True
except (ImportError, Exception):
    pass

from PyQt6.QtWidgets import QApplication
from src.core.config_manager import ConfigManager
from src.gui.first_run_wizard import FirstRunWizard
from src.gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)

    config = ConfigManager()
    if config.is_first_run():
        wizard = FirstRunWizard()
        if not wizard.exec():
            return 0

    window = MainWindow()
    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        import traceback

        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
