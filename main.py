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
    if os.environ.get("GOOGLE_CREDENTIALS"):
        creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
    
    client = gspread.authorize(creds)
    
    mes_actual_num = datetime.now().month
    nombre_hoja = MESES[mes_actual_num] 
    
    print(f"Buscando hoja del mes: {nombre_hoja}")
    
    try:
        # RECUERDA: Si cambiaste el nombre del archivo o quieres usar ID, edita esta linea
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
    
    fecha_hoy = datetime.now().strftime("%d/%m/%Y") 
    print(f"--- Iniciando revisión para fecha: {fecha_hoy} ---")

    encabezados = hoja.row_values(1)
    
    try:
        columna_destino_idx = encabezados.index(fecha_hoy) + 1
        print(f"Columna encontrada para hoy: {columna_destino_idx} ({fecha_hoy})")
    except ValueError:
        print(f"Error CRÍTICO: No encontré la columna '{fecha_hoy}' en la fila 1.")
        return

    cuentas = hoja.col_values(1) 
    
    for i in range(1, len(cuentas)):
        referencia = str(cuentas[i]).strip()
        fila_excel = i + 1 
        
        if not referencia or referencia.upper() == "CUENTA": 
            continue

        print(f"Consultando Cuenta: {referencia} (Fila {fila_excel})")
        
        # Consultamos (ahora con reintentos automáticos internos)
        resultado = scraper.consultar_referencia(referencia)
        
        valor_a_escribir = ""
        
        if "error" in resultado:
            error_msg = resultado['error']
            print(f"-> Resultado: ERROR ({error_msg})")
            
            if "Referencia no valida" in error_msg:
                valor_a_escribir = "ERROR REFERENCIA"
            else:
                valor_a_escribir = "ERROR CONEXION" # Para diferenciar si fue culpa del servidor
        
        elif resultado["estatus"] == "PAGADO":
            valor_a_escribir = "PAGADO"
            print("-> Resultado: PAGADO")
        else:
            valor_a_escribir = resultado["monto"]
            print(f"-> Resultado: DEUDA {valor_a_escribir}")
        
        try:
            hoja.update_cell(fila_excel, columna_destino_idx, valor_a_escribir)
            
            # PAUSA AUMENTADA: 5 segundos entre cuentas para evitar Error 504
            # Si tienes muchas cuentas y es muy lento, bájalo a 3, pero 5 es seguro.
            print("Esperando 5s para la siguiente...")
            time.sleep(5) 
            
        except Exception as e:
            print(f"Error escribiendo en Excel: {e}")

    print("--- Fin del proceso ---")

if __name__ == "__main__":
    job()
