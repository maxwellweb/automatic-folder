import json
import os
import sys

def get_file_path(relative_path):
    """
    Devuelve la ruta al archivo empaquetado o externo.
    """
    if getattr(sys, 'frozen', False):  # Si está empaquetado con PyInstaller
        base_path = sys._MEIPASS
    else:  # Modo desarrollo
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)


def load_config(file_path):
    """
    Carga el contenido de un archivo JSON.

    Args:
        file_path (str): Ruta al archivo JSON.

    Returns:
        dict: Configuración cargada desde el archivo JSON.
    """
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return json.load(file)
    raise FileNotFoundError(f"El archivo de configuración '{file_path}' no existe.")
