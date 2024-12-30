import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import gspread

def connect_to_google_sheet(sheet_url, credentials_file):
    """
    Conecta a un Google Sheet utilizando la URL y credenciales de la API.
    """
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
    client = gspread.authorize(credentials)
    
    try:
        sheet_id = sheet_url.split('/d/')[1].split('/')[0]
    except IndexError:
        raise ValueError("La URL proporcionada no es valida.")
    
    sheet = client.open_by_key(sheet_id).sheet1
    
    expected_headers = ["Carpeta", "Editor", "Fecha de descarga", "Estado"]
    records = sheet.get_all_records(expected_headers=expected_headers)
    
    return pd.DataFrame(records)

def load_excel_data(sheet_url, credentials_file):
    """
    Carga los datos desde un Google Sheet y asigna nombres a las columnas.
    """
    df = connect_to_google_sheet(sheet_url, credentials_file)
    return df

def append_row_to_google_sheet(sheet_url, credentials_file, row_data):
    """
    Agrega una fila a un Google Sheet utilizando la URL y credenciales de la API.
    """
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
    client = gspread.authorize(credentials)
    
    try:
        sheet_id = sheet_url.split('/d/')[1].split('/')[0]
    except IndexError:
        raise ValueError("La URL proporcionada no es valida.")
    
    sheet = client.open_by_key(sheet_id).sheet1
    
    sheet.append_row(row_data)

def update_row_in_google_sheet(sheet_url, credentials_file, folder_name, updated_data):
    """
    Actualiza una fila en un Google Sheet utilizando la URL y credenciales de la API.
    """
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
    client = gspread.authorize(credentials)
    
    try:
        sheet_id = sheet_url.split('/d/')[1].split('/')[0]
    except IndexError:
        raise ValueError("La URL proporcionada no es valida.")
    
    sheet = client.open_by_key(sheet_id).sheet1
    
    cell = sheet.find(folder_name)
    if not cell:
        raise ValueError(f"La carpeta '{folder_name}' no se encuentra en la planilla.")
    
    row_number = cell.row
    sheet.update(f"B{row_number}:D{row_number}", [updated_data])
    
def batch_update_google_sheet(sheet_url, credentials_file, data):
    from time import sleep
    """
    Actualiza varias filas en un Google Sheet en una sola solicitud.

    Args:
        sheet_url (str): URL de la planilla de Google Sheets.
        credentials_file (str): Ruta al archivo de credenciales.
        data (list of lists): Datos a actualizar, cada sublista representa una fila.

    Raises:
        ValueError: Si la URL o el formato de los datos no es válido.
    """
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
    client = gspread.authorize(credentials)
    
    try:
        sheet_id = sheet_url.split('/d/')[1].split('/')[0]
    except IndexError:
        raise ValueError("La URL proporcionada no es valida.")
    
    sheet = client.open_by_key(sheet_id).sheet1
    
    current_values = sheet.get_all_values()[1:]
    
    for row in data:
        folder_name = row[0]
        found = False
        for i, existing_row in enumerate(current_values, start=2):  # Excluir cabeceras, comienza en fila 2
            if folder_name == existing_row[0]:  # Carpeta encontrada, actualizar
                sheet.update(f"A{i}:D{i}", [row])
                found = True
                break
        if not found:  # Carpeta nueva, agregar al final
            sheet.append_row(row)
    
    