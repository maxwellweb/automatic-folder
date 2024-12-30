import json
import os
import sys

def get_file_path(relative_path):
    """
    Devuelve la ruta del archivo empaquetado o externo.
    """
    if getattr(sys, 'frozen', False):  # Si está empaquetado con PyInstaller
        base_path = sys._MEIPASS
    else:  # Modo desarrollo
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

# Rutas para los archivos empaquetados
FTP_CONFIG_FILE = get_file_path("credentials/ftp_config.json")
CREDENTIALS_FILE = get_file_path("credentials/credentials.json")

def load_config(file_path):
    """
    Carga el contenido de un archivo JSON.
    """
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return json.load(file)
    return {}

def save_config(file_path, config):
    """
    Guarda un archivo JSON en la ruta especificada.

    Args:
        file_path (str): Ruta al archivo JSON.
        config (dict): Configuración que se guardará.
    """
    
     # Cargar la configuración existente
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            existing_config = json.load(file)
    else:
        existing_config = {"ftp": {}}

    # Actualizar solo las claves de "ftp" sin duplicar ni anidar
    if "ftp" in config:
        for key, value in config["ftp"].items():
            existing_config["ftp"][key] = value
            
    # Asegurarse de que el directorio exista
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Guardar el archivo JSON
    with open(file_path, "w") as file:
        json.dump(existing_config, file, indent=4)