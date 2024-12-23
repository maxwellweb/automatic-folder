from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QFormLayout, QMessageBox


class FTPConfigDialog(QDialog):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.setWindowTitle("Configuración de FTP y Google Sheets")
        self.setGeometry(200, 200, 400, 350)

        self.config = config

        # Layout principal
        layout = QVBoxLayout()

        # Formulario
        form_layout = QFormLayout()

        self.host_input = QLineEdit(self.config.get("host", ""))
        self.user_input = QLineEdit(self.config.get("user", ""))
        self.password_input = QLineEdit(self.config.get("password", ""))
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)  # Ocultar contraseña
        self.base_path_input = QLineEdit(self.config.get("base_path", "/"))
        self.sheet_url_input = QLineEdit(self.config.get("google_sheet_url", ""))

        form_layout.addRow("Host:", self.host_input)
        form_layout.addRow("Usuario:", self.user_input)
        form_layout.addRow("Contraseña:", self.password_input)
        form_layout.addRow("Directorio Raíz:", self.base_path_input)
        form_layout.addRow("URL de Google Sheets:", self.sheet_url_input)

        layout.addLayout(form_layout)

        # Botones
        self.save_btn = QPushButton("Guardar")
        self.save_btn.clicked.connect(self.save_config)
        layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)

        self.setLayout(layout)

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

        self.config["host"] = host
        self.config["user"] = user
        self.config["password"] = password
        self.config["base_path"] = base_path
        self.config["google_sheet_url"] = sheet_url
        self.accept()
