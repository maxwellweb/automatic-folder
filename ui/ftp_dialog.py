from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QGridLayout, QMessageBox
)
from PyQt6.QtCore import Qt


class FTPConfigDialog(QDialog):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.setWindowTitle("Configuración de FTP y Google Sheets")
        self.setGeometry(200, 200, 500, 400)  # Tamaño inicial más amplio

        self.config = config

        # Layout principal
        main_layout = QVBoxLayout()

        # Título
        title_label = QLabel("Configura los detalles del servidor FTP y Google Sheets")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Formulario con GridLayout
        form_layout = QGridLayout()

        # Campos del formulario
        self.host_input = QLineEdit(self.config.get("ftp", {}).get("host", ""))
        self.user_input = QLineEdit(self.config.get("ftp", {}).get("user", ""))
        self.password_input = QLineEdit(self.config.get("ftp", {}).get("password", ""))
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)  # Ocultar contraseña
        self.base_path_input = QLineEdit(self.config.get("ftp", {}).get("base_path", "/"))
        self.sheet_url_input = QLineEdit(self.config.get("ftp", {}).get("google_sheet_url", ""))

        # Etiquetas
        form_layout.addWidget(QLabel("Host:"), 0, 0)
        form_layout.addWidget(self.host_input, 0, 1)

        form_layout.addWidget(QLabel("Usuario:"), 1, 0)
        form_layout.addWidget(self.user_input, 1, 1)

        form_layout.addWidget(QLabel("Contraseña:"), 2, 0)
        form_layout.addWidget(self.password_input, 2, 1)

        form_layout.addWidget(QLabel("Directorio Raíz:"), 3, 0)
        form_layout.addWidget(self.base_path_input, 3, 1)

        form_layout.addWidget(QLabel("URL de Google Sheets:"), 4, 0)
        form_layout.addWidget(self.sheet_url_input, 4, 1)

        # Ajustar proporciones de las columnas
        form_layout.setColumnStretch(0, 1)
        form_layout.setColumnStretch(1, 3)

        main_layout.addLayout(form_layout)

        # Botones
        button_layout = QVBoxLayout()
        self.save_btn = QPushButton("Guardar")
        self.save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def save_config(self):
        """
        Guarda la configuración ingresada y cierra el diálogo.
        """
        host = self.host_input.text().strip()
        user = self.user_input.text().strip()
        password = self.password_input.text().strip()
        base_path = self.base_path_input.text().strip()
        sheet_url = self.sheet_url_input.text().strip()

        if not all([host, user, password, base_path, sheet_url]):
            QMessageBox.warning(self, "Error", "Todos los campos son obligatorios.")
            return

        self.config["ftp"] = {
            "host": host,
            "user": user,
            "password": password,
            "base_path": base_path,
            "google_sheet_url": sheet_url,
        }
        self.accept()
