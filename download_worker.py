import json
import os
import sys
from PyQt6.QtCore import QObject, pyqtSignal
from ftplib import FTP


def get_file_path(relative_path):
    """
    Devuelve la ruta al archivo empaquetado o externo.
    """
    # Si está empaquetado con PyInstaller
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:  # En modo desarrollo
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)


def load_ftp_config(file_path):
    """
    Carga las credenciales del archivo JSON.

    Args:
        file_path: Ruta al archivo JSON con las credenciales.

    Returns:
        Un diccionario con las credenciales de FTP.
    """
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        raise Exception(f"El archivo de configuración '{file_path}' no existe.")
    except json.JSONDecodeError:
        raise Exception(f"Error al decodificar el archivo de configuración '{file_path}'.")


class DownloadWorker(QObject):
    progress = pyqtSignal(int, int, str)  # Señal para la barra de progreso
    finished = pyqtSignal(str)  # Señal para indicar que la descarga ha terminado
    error = pyqtSignal(str)  # Señal para indicar un error durante la descarga

    def __init__(self, ftp_config, remote_directory, local_directory):
        """
        Constructor del worker para manejar descargas FTP.

        Args:
            ftp_config_path: Ruta al archivo JSON con las credenciales de FTP.
            remote_directory: Directorio remoto en el servidor FTP.
            local_directory: Directorio local para descargar los archivos.
        """
        super().__init__()
        self.remote_directory = remote_directory
        self.local_directory = local_directory
        self.ftp_config = ftp_config  # Carga las credenciales

    def run(self):
        """
        Ejecuta la descarga en el hilo separado.
        """
        try:
            # Conectar al servidor FTP
            ftp = FTP()
            ftp.connect(self.ftp_config["host"], timeout=30)
            ftp.login(self.ftp_config["user"], self.ftp_config["password"])
            ftp.cwd(self.remote_directory)

            # Crear el directorio local si no existe
            os.makedirs(self.local_directory, exist_ok=True)

            # Descargar archivos y subdirectorios
            self.download_directory(ftp, self.remote_directory, self.local_directory)

            ftp.quit()

            # Emitir la señal de fin de descarga
            self.finished.emit("Descarga completada.")
        except Exception as e:
            # Emitir la señal de error
            self.error.emit(str(e))

    def download_directory(self, ftp, remote_directory, local_directory):
        """
        Descarga un directorio completo desde el servidor FTP al sistema local.

        Args:
            ftp: Conexión FTP.
            remote_directory: Ruta del directorio en el servidor FTP.
            local_directory: Ruta local donde se guardarán los archivos.
        """
        ftp.cwd(remote_directory)
        items = ftp.nlst()  # Obtener la lista de archivos y carpetas en el directorio remoto

        total_items = len(items)
        downloaded_files = 0

        for item in items:
            remote_path = f"{remote_directory}/{item}"
            local_path = os.path.join(local_directory, item)

            try:
                # Verificar si el elemento es un archivo o un directorio
                ftp.cwd(remote_path)  # Si se puede cambiar al directorio, es un directorio
                os.makedirs(local_path, exist_ok=True)  # Crear el directorio local
                self.download_directory(ftp, remote_path, local_path)  # Llamada recursiva
                ftp.cwd("..")  # Volver al directorio anterior
            except Exception:
                # Es un archivo, descargarlo
                with open(local_path, "wb") as f:
                    ftp.retrbinary(f"RETR {remote_path}", f.write)
                downloaded_files += 1
                self.progress.emit(downloaded_files, total_items, item)
