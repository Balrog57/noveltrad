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

if "--backend" in sys.argv or "--headless" in sys.argv:
    argv = [arg for arg in sys.argv[1:] if arg not in ("--backend", "--headless")]
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

if "--version" in sys.argv:
    from src import __version__
    print(f"NovelTrad v{__version__}")
    raise SystemExit(0)

from PyQt6.QtCore import QTranslator
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from src.gui.app_config import ConfigManager
from src.gui.first_run_wizard import FirstRunWizard
from src.gui.i18n import default_language, has_translation, load_translator
from src.gui.main_window import MainWindow


def _icon_path() -> str:
    """Return the absolute path to the app icon, works in dev and frozen builds."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base = root_dir
    ico = os.path.join(base, "assets", "noveltrad-icon.ico")
    if os.path.isfile(ico):
        return ico
    # fallback: try png
    png = os.path.join(base, "assets", "noveltrad-logo-256.png")
    return png if os.path.isfile(png) else ""


def _set_app_icon(app: QApplication) -> None:
    icon_path = _icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))


def main() -> int:
    # Catch-all exception hook for uncaught Python exceptions
    # (e.g. a signal-slot raising). Without this, Qt silently
    # terminates the app on the first uncaught exception.
    sys.excepthook = _global_excepthook
    app = QApplication(sys.argv)
    # Set app icon
    _set_app_icon(app)

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


def _global_excepthook(exc_type, exc_value, exc_tb) -> None:
    """Log uncaught exceptions to backend.log so we can
    diagnose Qt crashes that happen outside any Python try/except
    (for example a signal-slot failure).
    """
    try:
        import traceback as _tb
        lines = "".join(_tb.format_exception(exc_type, exc_value, exc_tb))
        _backend_debug_log("UNCAUGHT: " + lines)
    except Exception:
        pass


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
