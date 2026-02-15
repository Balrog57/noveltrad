import threading
import webview
import uvicorn
import sys
import os

# Add src to path if needed for relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api import app

def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

if __name__ == '__main__':
    # Start API in a thread
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()

    # Create window (Force Qt due to Python 3.14 / pythonnet issues)
    # debug=True allows right-click -> Inspect Element
    webview.create_window('NovelTrad', 'http://127.0.0.1:8000')
    webview.start(gui='qt', debug=True)
