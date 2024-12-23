import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import FolderManagerApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FolderManagerApp()
    window.show()
    sys.exit(app.exec())