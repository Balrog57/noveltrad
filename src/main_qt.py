import os
import sys
import multiprocessing as mp
from pathlib import Path

mp.freeze_support()


def _backend_debug_log(message: str) -> None:
    if not getattr(sys, "frozen", False):
        return
    try:
        path = (
            Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
            / "NovelTrad"
            / "backend.log"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    except Exception:
        pass

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

if "--backend" in sys.argv:
    argv = [arg for arg in sys.argv[1:] if arg != "--backend"]
    _backend_debug_log(f"backend argv={argv!r}")
    try:
        from src.gui.app_config import ConfigManager

        ConfigManager().apply_environment()
        _backend_debug_log("backend environment applied from user config")
    except Exception as exc:
        _backend_debug_log(f"backend config environment failed: {exc}")
    from src.backend.server import main as backend_main

    _backend_debug_log("backend_main imported")
    code = backend_main(argv)
    _backend_debug_log(f"backend_main exited code={code}")
    raise SystemExit(code)

from PyQt6.QtCore import QTranslator
from PyQt6.QtWidgets import QApplication
from src.gui.app_config import ConfigManager
from src.gui.first_run_wizard import FirstRunWizard
from src.gui.i18n import default_language, has_translation, load_translator
from src.gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    # Install UI translator (French today; English by default). Note:
    # language switching requires a restart in Qt — we only honour the
    # language at launch. The Settings combobox persists the choice
    # to ConfigManager; the next launch picks it up.
    language = default_language()
    if language and has_translation(language):
        translator = load_translator(language)
        if translator is not None:
            app.installTranslator(translator)

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
