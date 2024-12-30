import sys
import os
from PyQt6.QtCore import QThread, QTimer
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QPushButton, QLabel, QFileDialog, QWidget, QMessageBox, QTableWidget, QTableWidgetItem, QInputDialog, QProgressBar, QTabWidget
)
from ui.ftp_dialog import FTPConfigDialog
from config.settings import *
from config.utils import *
from ftp_config import load_config, save_config
from data.google_sheets import update_row_in_google_sheet, load_excel_data
from data.folder_analysis import connect_ftp, verificar_carpetas_ftp, close_ftp_connection
from workers.download import DownloadWorker
from workers.analyst_folder import AnalyzeWorker

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
        self.ftp_config = self.config.get("ftp",{})
        self.download_path = os.path.expanduser("~/Downloads")
        self.folder_states = {}  # Diccionario para gestionar el estado de las carpetas
        self.sheet_data = None  # Inicializa sheet_data
        self.timer = QTimer()
        self.timer.timeout.connect(self.analyze_folders)

    def open_config_dialog(self):
        """Abre el formulario para configurar credenciales FTP y Google Sheets."""
        dialog = FTPConfigDialog(self, self.config)
        if dialog.exec():
            config_path = get_file_path("credentials/ftp_config.json")
            save_config(config_path, self.config)
            self.google_sheet_url = self.config.get("google_sheet_url")
            QMessageBox.information(self, "Configuración Guardada", "La configuración ha sido guardada correctamente.")
            if bool(self.google_sheet_url) and all(self.ftp_config.values()):
                self.timer.start(30000)  # Inicia el análisis automático cada 10 segundos

    def analyze_folders(self):
        """Analiza las carpetas en el servidor FTP automáticamente."""
        self.worker = AnalyzeWorker(
            self.ftp_config,
            self.google_sheet_url,
            self.credential_path,
            self.folder_states
        )
        
        # conectar señales del trabajador con el hilo principal
        self.worker.message.connect(self.show_message)
        self.worker.update_tabs_signal.connect(self.hander_update_tabs)
        
        # Iniciar el hilo
        self.worker.start()

    def show_message(self, title, content):
        QMessageBox.information(self, title, content)
    
    def hander_update_tabs(self, update_folder_states, sheet_data):
        self.sheet_data = sheet_data
        self.folder_states = update_folder_states
        self.update_tabs()

    def update_tabs(self):
        """Actualiza las pestañas con carpetas disponibles y usadas."""
        if self.sheet_data is None:
            QMessageBox.warning(self, "Sin Datos", "No se han cargado datos de Google Sheets.")
            return
        
        available = [folder for folder, state in self.folder_states.items() if state == "disponible"]
        used = [
            (
                folder,
                self.sheet_data.loc[self.sheet_data["Carpeta"] == folder, "Editor"].values[0]
                if len(self.sheet_data.loc[self.sheet_data["Carpeta"] == folder, "Editor"].values) > 0
                else "Sin Editor"
            )
            for folder, state in self.folder_states.items() if state == "usada"
        ]

        self.available_table.setRowCount(len(available))
        self.available_table.setColumnCount(2)
        self.available_table.setHorizontalHeaderLabels(["Carpeta", "Estado"])
        for row, folder in enumerate(available):
            if folder:
                self.available_table.setItem(row, 0, QTableWidgetItem(folder))
            estado = self.folder_states.get(folder, "Desconocido")
            if estado:
                self.available_table.setItem(row, 1, QTableWidgetItem(estado))

        self.available_table.resizeColumnsToContents()

        self.used_table.setRowCount(len(used))
        self.used_table.setColumnCount(2)
        self.used_table.setHorizontalHeaderLabels(["Carpeta", "Editor"])
        for row, (folder, editor) in enumerate(used):
            if folder:
                self.used_table.setItem(row, 0, QTableWidgetItem(folder))
                
            if editor:
                self.used_table.setItem(row, 1, QTableWidgetItem(editor))

        self.used_table.resizeColumnsToContents()
    def download_and_update(self):
        """Descarga un directorio y actualiza Google Sheets."""
        selected_row = self.available_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Error", "Por favor, selecciona una carpeta disponible para descargar.")
            return
        
        selected_folder = self.available_table.item(selected_row, 0).text()
        
        sheet_data = load_excel_data(self.google_sheet_url, self.credential_path)
        folder_row = sheet_data[sheet_data["Carpeta"] == selected_folder]
        if not folder_row.empty:
            current_state = folder_row["Estado"].values[0]
            if current_state != "disponible":
                QMessageBox.warning(self, "Error", f"La carpeta '{selected_folder}' ya está siendo descargada por otro editor.")
                self.folder_states[selected_folder] = "en proceso"
                return

        # Marcar la carpeta como "en proceso"
        self.folder_states[selected_folder] = "en proceso"
        self.update_tabs()
        
        update_row_in_google_sheet(
            self.google_sheet_url,
            self.credential_path,
            selected_folder,
            ["", "", "en proceso"]
        )

        editor, ok = QInputDialog.getText(self, "Nombre del Editor", "Introduce tu nombre:")
        if not ok or not editor.strip():
            QMessageBox.warning(self, "Error", "El nombre del editor es obligatorio.")
            self.folder_states[selected_folder] = "disponible"  # Liberar el bloqueo si no se confirma
            self.update_tabs()
            update_row_in_google_sheet(
                self.google_sheet_url,
                self.credential_path,
                selected_folder,
                ["", "", "disponible"]
            )
            return
        
        base_path = self.ftp_config["base_path"]
        remote_directory = f"{base_path}/{selected_folder}"
        local_directory = os.path.join(self.download_path, selected_folder)
        os.makedirs(local_directory, exist_ok=True)

        self.thread = QThread()
        self.worker = DownloadWorker(self.ftp_config, remote_directory, local_directory)
        self.worker.moveToThread(self.thread)

        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(lambda msg: self.download_finished(msg, selected_folder, editor))
        self.worker.error.connect(self.handle_error)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.started.connect(self.worker.run)
        
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
            self.progress_label.setText(f"Progreso: {percentage}%")

    def handle_error(self, error_message):
        QMessageBox.critical(self, "Error", f"Error durante la descarga: {error_message}")
        for folder, state in self.folder_states.items():
            if state == "en proceso":
                self.folder_states[folder] = "disponible"
        self.update_tabs()
        self.progress_label.setText("Error durante la descarga.")
        self.progress_bar.setValue(0)
       
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()

    def download_finished(self, message, selected_folder, editor):
        from datetime import datetime  # Importar el módulo datetime
        QMessageBox.information(self, "Descarga completa", message)
        folder_name = selected_folder
        update_row_in_google_sheet(
            self.google_sheet_url,
            self.credential_path,
            folder_name,
            [
                editor, 
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                "descargada"
            ]
        )

        # Marcar como usada
        self.folder_states[selected_folder] = "usada"
        self.update_tabs()

        self.progress_bar.setValue(0)
        self.progress_label.setText("Descarga completada.")
        
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()

    def select_download_path(self):
        path = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Descarga", self.download_path)
        if path:
            self.download_path = path
            QMessageBox.information(self, "Carpeta de Descarga Seleccionada", f"Carpeta seleccionada: {self.download_path}")
