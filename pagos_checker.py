import requests
from bs4 import BeautifulSoup

class PagosDigitalesScraper:
    def __init__(self):
        self.base_url = "https://www.pagosdigitales.com/Website/Servicios/ConsultarSaldo/9a7bbd8b-c817-4071-9b60-1831dc2f3d4a"
        self.post_url = "https://www.pagosdigitales.com/Website/Gestopagos/ConsultarSaldo"
        self.session = requests.Session()
        # Headers actualizados según tu archivo Refnovalida.txt (Firefox 147.0)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://www.pagosdigitales.com",
            "Referer": self.base_url
        }
        self.session.headers.update(self.headers)

    def consultar_referencia(self, referencia):
        try:
            # PASO 1: Obtener el token de seguridad (GET)
            response_get = self.session.get(self.base_url)
            if response_get.status_code != 200:
                return {"error": "Error al cargar página de inicio"}

            soup = BeautifulSoup(response_get.text, 'html.parser')
            token_input = soup.find('input', {'name': '__RequestVerificationToken'})
            if not token_input:
                return {"error": "Token de seguridad no encontrado"}
            
            token = token_input['value']

            # PASO 2: Enviar los datos (POST)
            payload = {
                "id": "9a7bbd8b-c817-4071-9b60-1831dc2f3d4a",
                "hRef": "nulo",
                "fuente": "",
                "Referencia": referencia,
                "__RequestVerificationToken": token
            }

            response_post = self.session.post(self.post_url, data=payload)
            texto_respuesta = response_post.text

            # PASO 3: Analizar la respuesta

            # --- NUEVA VALIDACIÓN: ERROR DE REFERENCIA ---
            if "Referencia no valida" in texto_respuesta:
                return {"error": "Referencia no valida"}

            # Caso SIN DEUDA (PAGADO)
            if "Referencia sin adeudo" in texto_respuesta or "Referencia sin adeudo" in response_post.url:
                return {
                    "estatus": "PAGADO",
                    "monto": 0
                }
            
            # Caso CON DEUDA: Buscamos el precio
            soup_res = BeautifulSoup(texto_respuesta, 'html.parser')
            divs_info = soup_res.find_all("div", class_="border-info")
            monto_encontrado = "$0.00"
            
            for div in divs_info:
                texto = div.get_text(strip=True)
                if "$" in texto:
                    monto_encontrado = texto
                    break
            
            if "$" in monto_encontrado and monto_encontrado != "$0.00":
                return {
                    "estatus": "DEUDA",
                    "monto": monto_encontrado
                }
            else:
                return {"error": "Respuesta desconocida (No se detectó monto ni confirmación)"}

        except Exception as e:
            return {"error": str(e)}
