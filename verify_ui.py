import sys
import os
from PyQt6.QtWidgets import QApplication

# Add src to path
sys.path.append(os.path.join(os.getcwd()))

def test_launch():
    print("Starting test launch...")
    app = QApplication(sys.argv)
    
    try:
        from src.gui.mainwindow import MainWindow
        window = MainWindow()
        print("MainWindow instantiated successfully.")
        
        # Check for key widgets
        assert hasattr(window, 'dict_input'), "dict_input is missing"
        assert hasattr(window, 'dict_results'), "dict_results is missing"
        assert hasattr(window, 'glossary_list'), "glossary_list is missing"
        assert hasattr(window, 'ai_text'), "ai_text is missing"
        
        print("Essential UI widgets are present.")
        
        # Clean up
        window.close()
        return True
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_launch()
    sys.exit(0 if success else 1)
