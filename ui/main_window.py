import sys
import os
from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QPushButton, QLabel, QFileDialog, QWidget, QMessageBox, QTableWidget, QTableWidgetItem, QInputDialog, QProgressBar, QTabWidget
)
from ui.ftp_dialog import FTPConfigDialog
from config.settings import *
from config.utils import *
from ftp_config import load_config, save_config
from data.google_sheets import load_excel_data, append_row_to_google_sheet
from data.folder_analysis import connect_ftp, verificar_carpetas_ftp, close_ftp_connection
from download_worker import DownloadWorker

class FolderManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestor de Carpetas con Google Sheets")
        self.setGeometry(100, 100, 800, 600)

        self.setup_ui()
        self.setup_variables()

    def setup_ui(self):
        """Configura la interfaz de usuario."""
        self.layout = QVBoxLayout()

        self.label = QLabel("Gestiona carpetas en un servidor FTP y analiza datos de Google Sheets:")
        self.layout.addWidget(self.label)

        self.edit_ftp_btn = QPushButton("Configurar FTP y Google Sheets")
        self.edit_ftp_btn.clicked.connect(self.open_config_dialog)
        self.layout.addWidget(self.edit_ftp_btn)

        self.analyze_btn = QPushButton("Analizar Carpetas en FTP")
        self.analyze_btn.clicked.connect(self.analyze_folders)
        self.analyze_btn.setEnabled(False)
        self.layout.addWidget(self.analyze_btn)

        self.select_path_btn = QPushButton("Seleccionar Carpeta de Descarga")
        self.select_path_btn.clicked.connect(self.select_download_path)
        self.layout.addWidget(self.select_path_btn)

        self.download_btn = QPushButton("Descargar Directorio y Actualizar Planilla")
        self.download_btn.clicked.connect(self.download_and_update)
        self.layout.addWidget(self.download_btn)

        self.tab_widget = QTabWidget()
        self.layout.addWidget(self.tab_widget)

        self.available_tab = QWidget()
        self.tab_widget.addTab(self.available_tab, "Carpetas Disponibles")
        self.available_layout = QVBoxLayout(self.available_tab)
        self.available_table = QTableWidget()
        self.available_layout.addWidget(self.available_table)

        self.used_tab = QWidget()
        self.tab_widget.addTab(self.used_tab, "Carpetas en Uso")
        self.used_layout = QVBoxLayout(self.used_tab)
        self.used_table = QTableWidget()
        self.used_layout.addWidget(self.used_table)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Descargando: ")
        self.layout.addWidget(self.progress_label)

        self.container = QWidget()
        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)

    def setup_variables(self):
        """Inicializa las variables de estado."""
        config_path = get_file_path("credentials/ftp_config.json")
        self.credential_path = get_file_path("credentials/credentials.json")
        self.config = load_config(config_path)
        self.google_sheet_url = self.config.get("google_sheet_url", None)
        self.ftp_config = self.config.get("ftp", {})
        self.download_path = os.path.expanduser("~/Downloads")

    def open_config_dialog(self):
        """Abre el formulario para configurar credenciales FTP y Google Sheets."""
        dialog = FTPConfigDialog(self, self.config)
        if dialog.exec():
            config_path = get_file_path("credentials/ftp_config.json")
            save_config(config_path, self.config)
            self.google_sheet_url = self.config.get("google_sheet_url")
            QMessageBox.information(self, "Configuración Guardada", "La configuración ha sido guardada correctamente.")
            self.analyze_btn.setEnabled(bool(self.google_sheet_url))

    def update_tabs(self, used, available):
        """Actualiza las pestañas con carpetas disponibles y usadas."""
        def fill_table(table, data, headers):
            table.setRowCount(len(data))
            table.setColumnCount(len(headers))
            table.setHorizontalHeaderLabels(headers)
            for row, items in enumerate(data):
                for col, item in enumerate(items):
                    table.setItem(row, col, QTableWidgetItem(item))
            table.resizeColumnsToContents()

        fill_table(self.available_table, [(folder,) for folder in available], ["Carpetas Disponibles"])
        fill_table(self.used_table, used, ["Carpeta", "Editor"])

    def analyze_folders(self):
        """Analiza las carpetas en el servidor FTP."""
        try:
            self.validate_ftp_and_sheet_config()

            ftp = connect_ftp(self.ftp_config["host"], self.ftp_config["user"], self.ftp_config["password"])
            self.sheet_data = load_excel_data(self.google_sheet_url, self.credential_path)

            used, available = verificar_carpetas_ftp(ftp, self.ftp_config["base_path"], self.sheet_data, "Carpeta")
            close_ftp_connection(ftp)

            used_with_editor = [
                (folder, self.sheet_data.loc[self.sheet_data["Carpeta"] == folder, "Editor"].values[0]
                if len(self.sheet_data.loc[self.sheet_data["Carpeta"] == folder, "Editor"].values) > 0
                else "Sin Editor")
                for folder in used
            ]

            self.update_tabs(used_with_editor, available)
            QMessageBox.information(self, "Análisis Completo", "Análisis de carpetas completado.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al analizar carpetas: {e}")

    def validate_ftp_and_sheet_config(self):
        """Valida la configuración del FTP y Google Sheets."""
        required_keys = ["host", "user", "password", "base_path"]
        for key in required_keys:
            if key not in self.ftp_config or not self.ftp_config[key]:
                raise Exception(f"Falta la clave de configuración: {key}")

        if not self.google_sheet_url:
            raise Exception("URL de Google Sheets no configurada.")

    def download_and_update(self):
        """Descarga un directorio y actualiza Google Sheets."""
        if not self.google_sheet_url:
            QMessageBox.warning(self, "Error", "Por favor, carga los datos de Google Sheets primero.")
            return

        selected_row = self.available_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Error", "Por favor, selecciona una carpeta disponible.")
            return

        selected_folder = self.available_table.item(selected_row, 0).text()
        editor, ok = QInputDialog.getText(self, "Nombre del Editor", "Introduce tu nombre:")
        if not ok or not editor.strip():
            QMessageBox.warning(self, "Error", "El nombre del editor es obligatorio.")
            return
        
        base_path = self.ftp_config["base_path"]
        remote_directory = f"{base_path}/{selected_folder}"
        local_directory = os.path.join(self.download_path, selected_folder)
        os.makedirs(local_directory, exist_ok=True)

        self.thread = QThread()
        self.worker = DownloadWorker(self.ftp_config, remote_directory, local_directory)
        self.worker.moveToThread(self.thread)

        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(lambda msg: self.download_finished(msg, selected_row, selected_folder, editor))
        self.worker.error.connect(self.handle_error)

        self.thread.started.connect(self.worker.run)
        self.thread.finished.connect(self.thread.deleteLater)

        self.progress_bar.setValue(0)
        self.progress_label.setText("Descargando: ")
        self.thread.start()

    def update_progress(self, current, total, filename=None):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        percentage = int((current / total) * 100)
        if filename:
            self.progress_label.setText(f"Descargando: {filename} ({percentage}%)")
        else:
            self.progress_label.setText(f"Progreso: ({percentage}%)")
            
    def handle_error(self, error_message):
        QMessageBox.critical(self, "Error", f"Error durante la descarga: {error_message}")
        self.progress_bar.setValue(0)
        self.thread.quit()

    def download_finished(self, message, selected_row, selected_folder, editor):
        QMessageBox.information(self, "Descarga completa", message)
        append_row_to_google_sheet(self.google_sheet_url, self.credential_path, [selected_folder, editor])

        self.available_table.removeRow(selected_row)
        row_position = self.used_table.rowCount()
        self.used_table.insertRow(row_position)
        self.used_table.setItem(row_position, 0, QTableWidgetItem(selected_folder))
        self.used_table.setItem(row_position, 1, QTableWidgetItem(editor))

        self.progress_bar.setValue(0)
        self.thread.quit()

    def select_download_path(self):
        path = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Descarga", self.download_path)
        if path:
            self.download_path = path
            QMessageBox.information(self, "Carpeta de Descarga Seleccionada", f"Carpeta seleccionada: {self.download_path}")
