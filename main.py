import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
from pagos_checker import PagosDigitalesScraper
import json

# Mapeo de meses para saber qué hoja buscar
MESES = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL", 5: "MAYO", 6: "JUNIO",
    7: "JULIO", 8: "AGOSTO", 9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
}

def get_google_sheet():
    # Carga de credenciales (compatible con Railway y Local)
    if os.environ.get("GOOGLE_CREDENTIALS"):
        creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
    
    client = gspread.authorize(creds)
    
    # 1. Determinar el nombre de la hoja según el mes actual
    mes_actual_num = datetime.now().month
    nombre_hoja = MESES[mes_actual_num] # Ej: "FEBRERO"
    
    print(f"Buscando hoja del mes: {nombre_hoja}")
    
    # Abre el archivo (CAMBIA 'NombreDeTuArchivo' POR EL NOMBRE REAL DE TU EXCEL)
    # Ejemplo: Si tu archivo se llama "Control Pagos 2026", pon eso.
    archivo = client.open_by_key("1i2bjo43U23-2wxtCBmc0jYeR3Vps5nl29cm-6lsRRjM")
    
    try:
        worksheet = archivo.worksheet(nombre_hoja)
        return worksheet
    except gspread.WorksheetNotFound:
        print(f"Error: No existe la pestaña llamada '{nombre_hoja}'")
        return None

def job():
    hoja = get_google_sheet()
    if not hoja:
        return

    scraper = PagosDigitalesScraper()
    
    # 2. Obtener fecha de hoy para buscar la columna
    # Formato debe coincidir con tu Excel: DD/MM/YYYY
    fecha_hoy = datetime.now().strftime("%d/%m/%Y") 
    print(f"--- Iniciando revisión para fecha: {fecha_hoy} ---")

    # Leer encabezados (Fila 1)
    encabezados = hoja.row_values(1)
    
    try:
        # Buscamos en qué índice (columna) está la fecha de hoy. 
        # Sumamos 1 porque gspread usa índices base 1 (A=1, B=2...)
        columna_destino_idx = encabezados.index(fecha_hoy) + 1
        print(f"Columna encontrada para hoy: {columna_destino_idx} ({fecha_hoy})")
    except ValueError:
        print(f"Error CRÍTICO: No encontré la columna '{fecha_hoy}' en la fila 1.")
        print("Asegúrate de haber creado la columna en el Excel.")
        return

    # Leer columna A (Cuentas)
    cuentas = hoja.col_values(1) # Esto devuelve una lista con toda la columna A
    
    # Iteramos las cuentas (saltamos el encabezado que es el índice 0)
    for i in range(1, len(cuentas)):
        referencia = str(cuentas[i]).strip()
        fila_excel = i + 1 # +1 porque Excel empieza en fila 1
        
        if not referencia or referencia == "CUENTA": 
            continue

        print(f"Consultando Cuenta: {referencia} (Fila {fila_excel})")
        
        # Consultamos a la web
        resultado = scraper.consultar_referencia(referencia)
        
        valor_a_escribir = ""
        
        if "error" in resultado:
            print(f"Error: {resultado['error']}")
            valor_a_escribir = "ERROR"
        elif resultado["estatus"] == "PAGADO":
            valor_a_escribir = "PAGADO"
        else:
            # Tiene deuda, ponemos el monto
            valor_a_escribir = resultado["monto"]
            
        print(f"Resultado: {valor_a_escribir}")
        
        # Escribimos en la celda correspondiente (Fila Cuenta x Columna Hoy)
        try:
            hoja.update_cell(fila_excel, columna_destino_idx, valor_a_escribir)
            time.sleep(1.5) # Pausa pequeña para no saturar
        except Exception as e:
            print(f"Error escribiendo en Excel: {e}")

    print("--- Fin del proceso ---")

if __name__ == "__main__":
    job()
