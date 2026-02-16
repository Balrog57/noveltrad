import subprocess
import sys
import os

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
        subprocess.check_call(["pyinstaller", "build.spec", "--noconfirm"])
        print("Build successful! Executable in dist/NovelTrad/")
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build()
