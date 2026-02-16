import os
import requests

ICONS = [
    "auto_stories", "folder_open", "save", "file_download", "settings", 
    "add", "check_circle", "cloud_done", "done_all", "content_copy", 
    "undo", "psychology", "bolt", "thumb_up", "thumb_down", 
    "menu_book", "open_in_new", "person", "history", "cloud_sync",
    "close", "minimize", "maximize" # Window controls just in case
]

BASE_URL = "https://fonts.gstatic.com/s/i/materialiconsround/{}/v15/24px.svg"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "resources", "icons")

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def download_icon(icon_name):
    urls = [
        BASE_URL.format(icon_name),
        f"https://fonts.gstatic.com/s/i/materialicons/{icon_name}/v6/24px.svg",
        f"https://fonts.gstatic.com/s/i/materialiconsoutlined/{icon_name}/v6/24px.svg",
        f"https://fonts.gstatic.com/s/i/materialiconsround/{icon_name}/v6/24px.svg"
    ]
    for url in urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                file_path = os.path.join(OUTPUT_DIR, f"{icon_name}.svg")
                with open(file_path, "wb") as f:
                    f.write(response.content)
                print(f"Downloaded: {icon_name}")
                return
        except:
            pass
    print(f"Failed to download {icon_name} from all sources")

if __name__ == "__main__":
    print(f"Downloading {len(ICONS)} icons to {OUTPUT_DIR}...")
    for icon in ICONS:
        download_icon(icon)
    print("Done.")
