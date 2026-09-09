"""
Entry point for xTS Pre-Setup UI Tool.
"""
import sys
import os
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Ensure current working directory is the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    config_path = os.path.join(script_dir, "config.json")
    window = MainWindow(config_path=config_path)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
