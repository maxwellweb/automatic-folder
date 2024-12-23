import sys
import os

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from download_worker import DownloadWorker
from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QPushButton, QLabel, QFileDialog, QWidget, QMessageBox, QTableWidget, QTableWidgetItem, QInputDialog, QProgressBar, QTabWidget
)
from ui.ftp_dialog import FTPConfigDialog
from config.settings import *
from config.utils  import *
from ftp_config import load_config, save_config
from data.google_sheets import load_excel_data, append_row_to_google_sheet
from data.folder_analysis import connect_ftp, verificar_carpetas_ftp, close_ftp_connection, download_directory

class FolderManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestor de Carpetas con Google Sheets")
        self.setGeometry(100, 100, 800, 600)

        self.layout = QVBoxLayout()

        self.label = QLabel("Gestiona carpetas en un servidor FTP y analiza datos de Google Sheets:")
        self.layout.addWidget(self.label)

        # self.select_credentials_btn = QPushButton("Cargar Credenciales JSON")
        # self.select_credentials_btn.clicked.connect(self.load_credentials)
        # self.layout.addWidget(self.select_credentials_btn)
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
        
        # Tabs
        self.tab_widget = QTabWidget()
        self.layout.addWidget(self.tab_widget)
        
        # Pestaña: Carpetas disponibles
        self.available_tab = QWidget()
        self.tab_widget.addTab(self.available_tab, "Carpetas Disponibles")
        self.available_layout = QVBoxLayout(self.available_tab)
        self.available_table = QTableWidget()
        self.available_layout.addWidget(self.available_table)
        
        # Pestaña: Carpetas en uso
        self.used_tab = QWidget()
        self.tab_widget.addTab(self.used_tab, "Carpetas en Uso")
        self.used_layout = QVBoxLayout(self.used_tab)
        self.used_table = QTableWidget()
        self.used_layout.addWidget(self.used_table)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)  # Inicialmente en 0%
        self.layout.addWidget(self.progress_bar)

        # self.table = QTableWidget()
        # self.layout.addWidget(self.table)

        self.container = QWidget()
        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)

        # Ruta al archivo de configuración
        config_path = get_file_path("credentials/ftp_config.json")
        
        # Cargar configuración desde el archivo
        self.config = load_config(config_path)  # Aquí se pasa el argumento correctamente
        
        # Variables de estado
        self.credentials_file = DEFAULT_CREDENTIALS_FILE
        self.sheet_data = None
        self.google_sheet_url = self.config.get("google_sheet_url", None)
        self.ftp_config = load_config(config_path)  # Cargar configuración de FTP
        # **Inicialización de la ruta de descarga**
        self.download_path = os.path.expanduser("~/Downloads")  # Ruta predeterminada de descargas

    def open_config_dialog(self):
        """
        Abre el formulario para configurar las credenciales FTP y Google Sheets.
        """
        dialog = FTPConfigDialog(self, self.config)
        if dialog.exec():
            # Ruta al archivo de configuración
            config_path = get_file_path("credentials/ftp_config.json")
            
            save_config(config_path, self.config)  # Guardar configuración en archivo
            self.google_sheet_url = self.config.get("google_sheet_url")
            QMessageBox.information(self, "Configuración Guardada", "La configuración ha sido guardada correctamente.")
            self.analyze_btn.setEnabled(bool(self.google_sheet_url))
            
    def update_tabs(self, used, available):
        """
        Actualiza las pestañas con carpetas disponibles y usadas.

        Args:
            used (list of tuples): Lista de carpetas usadas con sus editores [(carpeta, editor)].
            available (list): Lista de carpetas disponibles [carpeta1, carpeta2, ...].
        """
        # Actualizar la tabla de carpetas disponibles
        self.available_table.setRowCount(len(available))
        self.available_table.setColumnCount(1)
        self.available_table.setHorizontalHeaderLabels(["Carpetas Disponibles"])
        for row, folder in enumerate(available):
            self.available_table.setItem(row, 0, QTableWidgetItem(folder))
        self.available_table.resizeColumnsToContents()

        # Actualizar la tabla de carpetas usadas
        self.used_table.setRowCount(len(used))
        self.used_table.setColumnCount(2)
        self.used_table.setHorizontalHeaderLabels(["Carpeta", "Editor"])
        for row, (folder, editor) in enumerate(used):
            self.used_table.setItem(row, 0, QTableWidgetItem(folder))
            self.used_table.setItem(row, 1, QTableWidgetItem(editor))
        self.used_table.resizeColumnsToContents()

    def load_credentials(self):
        """
        Selecciona el archivo de credenciales JSON.
        """
        self.credentials_file, _ = QFileDialog.getOpenFileName(self, "Seleccionar Credenciales JSON", "", "Archivos JSON (*.json)")
        if self.credentials_file:
            QMessageBox.information(self, "Credenciales Seleccionadas", f"Archivo de credenciales seleccionado: {self.credentials_file}")
        else:
            QMessageBox.warning(self, "Advertencia", "Por favor, selecciona un archivo de credenciales JSON.")

    def load_google_sheet_data(self):
        """
        Solicita una URL de Google Sheets al usuario y carga los datos utilizando las credenciales.
        """
        if not self.credentials_file:
            QMessageBox.warning(self, "Error", "Por favor, selecciona el archivo de credenciales JSON primero.")
            return

        # Solicitar URL de Google Sheets al usuario
        sheet_url, ok = QInputDialog.getText(self, "Cargar Datos de Google Sheets", "Introduce la URL del Google Sheet:")
        if not ok or not sheet_url.strip():
            QMessageBox.warning(self, "Error", "La URL proporcionada no es válida.")
            return

        try:
            # Guardar la URL en self.google_sheet_url
            self.google_sheet_url = sheet_url.strip()
            
            # Cargar los datos desde Google Sheets
            self.sheet_data = load_excel_data(sheet_url.strip(), self.credentials_file)
            QMessageBox.information(self, "Datos Cargados", "Datos del Google Sheet cargados correctamente.")
            self.analyze_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar datos de Google Sheets: {e}")

    def analyze_folders(self):
        """
        Analiza las carpetas en el servidor FTP.
        """
        if not self.config or not all(key in self.config for key in ["host", "user", "password", "base_path"]):
            QMessageBox.warning(self, "Error", "Por favor, configure las credenciales de FTP primero.")
            return
        
        host = self.ftp_config.get("host")
        user = self.ftp_config.get("user")
        password = self.ftp_config.get("password")
        base_path = self.ftp_config.get("base_path")
        sheet_url = self.config.get("google_sheet_url")
        
        if not all([host, user, password, base_path, sheet_url]):
            QMessageBox.warning(self, "Error", "Por favor, configure las credenciales de FTP primero.")
            return
        
        try:
            try:
                ftp = connect_ftp(host, user, password)
                self.sheet_data = load_excel_data(sheet_url, "credentials/credentials.json")
                used, available = verificar_carpetas_ftp(ftp, base_path, self.sheet_data, "Carpeta")
                close_ftp_connection(ftp)
                
                QMessageBox.information(self, "Análisis Completo", "Análisis de carpetas completado.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"{e}")
                return
            
            used_with_editor = []
            for folder in used:
                # Buscamos el editor asociado a la carpeta en self.sheet_data
                editor = self.sheet_data.loc[self.sheet_data["Carpeta"] == folder, "Editor"].values
                editor_name = editor[0] if len(editor) > 0 else "Sin Editor"
                used_with_editor.append((folder, editor_name))
            
            self.update_tabs(used_with_editor, available)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al analizar carpetas: {e}")
    
    def update_progress(self, current, total):
        """
        Actualiza la barra de progreso durante la descarga.
        """
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
    
    def handle_error(self, error_message):
        """
        Maneja errores durante la descarga.
        """
        QMessageBox.critical(self, "Error", f"Error durante la descarga: {error_message}")
        self.progress_bar.setValue(0)
        self.thread.quit()

    def select_download_path(self):
        """
        Permite al usuario seleccionar la carpeta de descarga.
        """
        path = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Descarga", self.download_path)
        if path:
            self.download_path = path
            QMessageBox.information(self, "Carpeta de Descarga Seleccionada", f"Carpeta seleccionada: {self.download_path}")

    def download_finished(self, message, selected_row, selected_folder, editor):
        """
        Finaliza la descarga, actualiza Google Sheets y las tablas de la interfaz.
        """
        QMessageBox.information(self, "Descarga completa", message)

        # Actualizar Google Sheets
        append_row_to_google_sheet(self.google_sheet_url, self.credentials_file, [selected_folder, editor])

        # Actualizar las tablas
        self.available_table.removeRow(selected_row)
        row_position = self.used_table.rowCount()
        self.used_table.insertRow(row_position)
        self.used_table.setItem(row_position, 0, QTableWidgetItem(selected_folder))
        self.used_table.setItem(row_position, 1, QTableWidgetItem(editor))

        # Resetear barra de progreso
        self.progress_bar.setValue(0)
        self.thread.quit()
    
    def download_and_update(self):
        """
        Descarga el directorio seleccionado de la lista de disponibles en un hilo separado
        y actualiza Google Sheets al finalizar.
        """
        if self.google_sheet_url is None or not self.google_sheet_url.strip():
            QMessageBox.warning(self, "Error", "Por favor, carga los datos de Google Sheets primero.")
            return

        if self.sheet_data is None or self.sheet_data.empty:
            QMessageBox.warning(self, "Error", "Por favor, analiza las carpetas primero.")
            return

        # Verificar si se seleccionó una carpeta en la lista de disponibles
        selected_row = self.available_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Error", "Por favor, selecciona una carpeta de la lista de disponibles.")
            return

        # Obtener el nombre de la carpeta seleccionada
        selected_folder = self.available_table.item(selected_row, 0).text()
        if not selected_folder:
            QMessageBox.warning(self, "Error", "La carpeta seleccionada no es válida.")
            return

        # Solicitar un nombre de editor
        editor, ok = QInputDialog.getText(self, "Nombre del Editor", "Introduce tu nombre:")
        if not ok or not editor.strip():
            QMessageBox.warning(self, "Error", "El nombre del editor es obligatorio.")
            return

        # Configuración del FTP
        ftp_config = {
            "host": FTP_HOST,
            "user": FTP_USER,
            "pass": FTP_PASS
        }
        remote_directory = f"/LAPENNA/ZALANDO/VIDEO/2024-12-18/DESIGNER/{selected_folder}"
        local_directory = os.path.join(self.download_path, selected_folder)
        
        try:
            os.makedirs(local_directory, exist_ok=True) 
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al crear la carpeta de descarga: {e}")
            return
        
        # Crear un hilo y un worker para la descarga
        self.thread = QThread()
        self.worker = DownloadWorker(ftp_config, remote_directory, local_directory)
        self.worker.moveToThread(self.thread)

        # Conectar señales del worker
        self.worker.progress.connect(self.update_progress)  # Conexión al método definido
        self.worker.finished.connect(lambda msg: self.download_finished(msg, selected_row, selected_folder, editor))
        self.worker.error.connect(self.handle_error)
        self.thread.started.connect(self.worker.run)
        self.thread.finished.connect(self.thread.deleteLater)

        # Iniciar el hilo
        self.progress_bar.setValue(0)
        self.thread.start()
        
        QMessageBox.information(self, "Descarga completa", f"Archivos descargados en {local_directory}.")
            
def update_tabs(self, used, available):
    """
    Actualiza las pestañas con carpetas disponibles y usadas.

    Args:
        used (list of tuples): Lista de carpetas usadas con sus editores [(carpeta, editor)].
        available (list): Lista de carpetas disponibles [carpeta1, carpeta2, ...].
    """
    # Actualizar la tabla de carpetas disponibles
    self.available_table.setRowCount(len(available))
    self.available_table.setColumnCount(1)
    self.available_table.setHorizontalHeaderLabels(["Carpetas Disponibles"])
    for row, folder in enumerate(available):
        self.available_table.setItem(row, 0, QTableWidgetItem(folder))
    self.available_table.resizeColumnsToContents()

    # Actualizar la tabla de carpetas usadas
    self.used_table.setRowCount(len(used))
    self.used_table.setColumnCount(2)
    self.used_table.setHorizontalHeaderLabels(["Carpeta", "Editor"])
    for row, (folder, editor) in enumerate(used):
        self.used_table.setItem(row, 0, QTableWidgetItem(folder))
        self.used_table.setItem(row, 1, QTableWidgetItem(editor))
    self.used_table.resizeColumnsToContents()

            
        