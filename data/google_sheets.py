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
    
    expected_headers = ["Carpeta", "Editor"]
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