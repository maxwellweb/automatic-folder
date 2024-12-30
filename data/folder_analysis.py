import os
from ftplib import FTP, error_perm

def connect_ftp(host, username, password, timeout=30):
    """
    Conecta al servidor FTP y retorna el objeto FTP.
    """
    if not isinstance(host, str) or not host.strip():
        raise ValueError("El host proporcionado no es válido. Debe ser una cadena no vacía.")
    
    print(f"Intentando conectar al servidor FTP: {host}")
    try:
        ftp = FTP()
        ftp.connect(host, timeout=timeout)
        ftp.login(user=username, passwd=password)
        ftp.set_pasv(True)
        return ftp
    except error_perm as e:
        raise ConnectionError(f"Error al conectar al servidor FTP: {e}")
    except ConnectionRefusedError:
        raise ConnectionError(f"El servidor FTP rechazó la conexión. Verifica que el servidor está activo y accesible.")
    except TimeoutError:
        raise ConnectionError("El tiempo de espera para la conexión FTP ha expirado.")
    except Exception as e:
        raise ConnectionError(f"Error al conectar al servidor FTP: {e}")


def list_folders_ftp(ftp, base_path):
    """
    Lista las carpetas en el directorio especificado en el servidor FTP.
    """
    try:
        ftp.cwd(base_path)
        return ftp.nlst()
    except Exception as e:
        raise IOError(f"Error al listar carpetas en {base_path}: {e}")


def verificar_carpetas_ftp(ftp, base_path, excel_data, column_folder_name):
    """
    Verifica cuáles carpetas están en uso y cuáles están disponibles en el servidor FTP.
    """
    try:
        # Listar carpetas desde el servidor FTP
        folders_in_directory = set(list_folders_ftp(ftp, base_path))
        # Carpetas en uso según el archivo Excel
        folders_in_use = set(excel_data[column_folder_name])
        
        # Comparar carpetas
        used_folders = folders_in_directory.intersection(folders_in_use)
        available_folders = folders_in_directory.difference(folders_in_use)
        
        return used_folders, available_folders
    except Exception as e:
        raise RuntimeError(f"Error al verificar carpetas: {e}")
    
def download_directory(ftp, remote_directory, local_directory, progress_callback=None):
    """
    Descarga un directorio completo desde el servidor FTP.
    """
    os.makedirs(local_directory, exist_ok=True)
    ftp.cwd(remote_directory)
    files = ftp.nlst()
    
    total_files = len(files)
    for i, file in enumerate(files, start=1):
        local_path = os.path.join(local_directory, file)
        try:
            with open(local_path, "wb") as f:
                ftp.retrbinary(f"RETR {file}", f.write)
        except Exception as e:
            print(f"Error al descargar {file}: {e}")
        
        # Actualizar la barra de progreso
        if progress_callback is not None:
            progress_callback(i, total_files)
    
    print(f"Directorio {remote_directory} descargado en {local_directory}")

def close_ftp_connection(ftp):
    """
    Cierra la conexión con el servidor FTP.
    """
    try:
        ftp.quit()
    except Exception as e:
        print(f"Error al cerrar la conexión FTP: {e}")
