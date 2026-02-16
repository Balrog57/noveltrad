import sys
import os
import logging

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.language_manager import LanguageManager

logging.basicConfig(level=logging.INFO)

def main():
    print("Initializing LanguageManager...")
    manager = LanguageManager()
    
    print("\nGetting Supported Languages (Intersection)...")
    langs = manager.get_supported_languages()
    print(f"Found {len(langs)} languages.")
    for lang in langs[:10]:
        print(f" - {lang['name']} ({lang['code']})")
    if len(langs) > 10:
        print(" ...")

    # Check for specific languages
    codes = [l['code'] for l in langs]
    required = ['fr', 'en', 'zh', 'ja']
    for req in required:
        status = "OK" if req in codes else "MISSING"
        print(f"Language {req}: {status}")

    print("\nSimulating Installation of 'fr' (French)...")
    # We use a callback to see progress
    def callback(msg, val):
        print(f"[Install] {val}% - {msg}")
        
    # We won't actually install to avoid large downloads if possible, 
    # but the download_kaikki_dict is relatively small for testing if we confirm it starts.
    # However, NLLB is large. Dictionary is small-ish (gzip). Argos is small-ish.
    # We might just call it and interrupt or just trust the logic if unit tests were better.
    # For now, let's just dry-run the manager's logic if possible, or just run it and see.
    # I'll comment it out to avoid actual download unless I want to verify connectivity.
    # manager.install_language_pack('fr', callback=callback)
    
    print("\nDone.")

if __name__ == "__main__":
    main()
