import subprocess
import sys
import os
from pathlib import Path

def build():
    print("Building NovelTrad...")
    
    # Ensure requirements are installed?
    # subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Clean build dirs
    import shutil
    if os.path.exists("build"): shutil.rmtree("build")
    if os.path.exists("dist"): shutil.rmtree("dist")
    
    # Run PyInstaller
    try:
        subprocess.check_call([sys.executable, "-m", "PyInstaller", "build.spec", "--noconfirm"])
        print("Build successful! Executable in dist/NovelTrad/")
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit(1)

    iscc = find_iscc()
    if iscc is None:
        print("Inno Setup compiler not found; skipped installer build.")
        return
    try:
        subprocess.check_call([str(iscc), "NovelTrad.iss"])
        print("Installer built: Setup_NovelTrad.exe")
    except subprocess.CalledProcessError as e:
        print(f"Installer build failed: {e}")
        sys.exit(1)


def find_iscc() -> Path | None:
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
        Path("C:/Program Files/Inno Setup 6/ISCC.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None

if __name__ == "__main__":
    build()
