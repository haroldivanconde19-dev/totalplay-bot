import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
from pagos_checker import PagosDigitalesScraper
import json

# Mapeo de meses
MESES = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL", 5: "MAYO", 6: "JUNIO",
    7: "JULIO", 8: "AGOSTO", 9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
}

def get_google_sheet():
    # Carga de credenciales
    if os.environ.get("GOOGLE_CREDENTIALS"):
        creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
    
    client = gspread.authorize(creds)
    
    # Busca la pestaña del mes actual
    mes_actual_num = datetime.now().month
    nombre_hoja = MESES[mes_actual_num] 
    
    print(f"Buscando hoja del mes: {nombre_hoja}")
    
    # Usa el ID que ya tenías configurado
    try:
        archivo = client.open_by_key("1i2bjo43U23-2wxtCBmc0jYeR3Vps5nl29cm-6lsRRjM")
        worksheet = archivo.worksheet(nombre_hoja)
        return worksheet
    except Exception as e:
        print(f"Error al abrir hoja: {e}")
        return None

def job():
    hoja = get_google_sheet()
    if not hoja:
        return

    scraper = PagosDigitalesScraper()
    
    # Fecha de hoy formato DD/MM/YYYY
    fecha_hoy = datetime.now().strftime("%d/%m/%Y") 
    print(f"--- Iniciando revisión para fecha: {fecha_hoy} ---")

    # Leer encabezados
    encabezados = hoja.row_values(1)
    
    try:
        columna_destino_idx = encabezados.index(fecha_hoy) + 1
        print(f"Columna encontrada para hoy: {columna_destino_idx} ({fecha_hoy})")
    except ValueError:
        print(f"Error CRÍTICO: No encontré la columna '{fecha_hoy}' en la fila 1.")
        return

    # Leer todas las cuentas (Columna A)
    cuentas = hoja.col_values(1) 
    
    # Iteramos saltando el encabezado
    for i in range(1, len(cuentas)):
        referencia = str(cuentas[i]).strip()
        fila_excel = i + 1 
        
        if not referencia or referencia.upper() == "CUENTA": 
            continue

        print(f"Consultando Cuenta: {referencia} (Fila {fila_excel})")
        
        # Consultamos a la web
        resultado = scraper.consultar_referencia(referencia)
        
        valor_a_escribir = ""
        
        # Lógica de qué escribir en el Excel
        if "error" in resultado:
            print(f"-> Error detectado: {resultado['error']}")
            # Escribir ERROR si falla la referencia
            valor_a_escribir = "ERROR"
        elif resultado["estatus"] == "PAGADO":
            valor_a_escribir = "PAGADO"
        else:
            # Tiene deuda
            valor_a_escribir = resultado["monto"]
            
        print(f"-> Resultado final: {valor_a_escribir}")
        
        # Escribimos en la celda
        try:
            hoja.update_cell(fila_excel, columna_destino_idx, valor_a_escribir)
            time.sleep(1.5) 
        except Exception as e:
            print(f"Error escribiendo en Excel: {e}")

    print("--- Fin del proceso ---")

if __name__ == "__main__":
    job()
