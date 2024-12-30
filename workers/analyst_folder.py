from PyQt6.QtCore import QThread, pyqtSignal

from data.folder_analysis import connect_ftp
from data.google_sheets import append_row_to_google_sheet, load_excel_data, batch_update_google_sheet

class AnalyzeWorker(QThread):
    message = pyqtSignal(str, str)  # Señal para enviar mensajes (título, contenido)
    update_tabs_signal = pyqtSignal(dict, object)

    def __init__(self, ftp_config, google_sheet_url, credential_path, folder_states):
        super().__init__()
        self.ftp_config = ftp_config
        self.google_sheet_url = google_sheet_url
        self.credential_path = credential_path
        self.folder_states = folder_states

    def run(self):
        from time import sleep
        import os
        
        sheet_data = None  # Inicializa sheet_data como None

        try:
            # Conexión al servidor FTP
            ftp = connect_ftp(self.ftp_config["host"], self.ftp_config["user"], self.ftp_config["password"])
            all_folders = ftp.nlst(self.ftp_config["base_path"])
            ftp.quit()

            folder_names = [os.path.basename(folder) for folder in all_folders]
            sheet_data = load_excel_data(self.google_sheet_url, self.credential_path)

            if sheet_data is None or sheet_data.empty:
                self.message.emit("Sincronización", "La planilla está vacía. Sincronizando con el servidor FTP...")
                
                batch_data = [[folder_name, "", "", "disponible"] for folder_name in folder_names]
                batch_update_google_sheet(self.google_sheet_url, self.credential_path, batch_data)                

                self.message.emit("Sincronización", "Sincronización completada.")
            else:
                used_folders = sheet_data[sheet_data["Estado"] == "descargada"]["Carpeta"].tolist()
                batch_data = []
                
                for folder_name in folder_names:
                    # Si la carpeta ya está en proceso o descargada, no sobrescribir
                    if folder_name in self.folder_states:
                        continue
                    
                    if folder_name in used_folders:
                        self.folder_states[folder_name] = "usada"
                    else:
                        self.folder_states[folder_name] = "disponible"
                        batch_data.append([folder_name, "", "", "disponible"])
                if batch_data:
                    batch_update_google_sheet(self.google_sheet_url, self.credential_path, batch_data)
                 
                # Emitirsenal para actualizar las tablas
                self.update_tabs_signal.emit(self.folder_states, sheet_data)
        except Exception as e:
            self.message.emit("Error", f"Error al analizar carpetas: {e}")
