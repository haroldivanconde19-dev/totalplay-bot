import requests
from bs4 import BeautifulSoup

class PagosDigitalesScraper:
    def __init__(self):
        # URL detectada en tu archivo PDADEUDO.txt [cite: 3]
        self.base_url = "https://www.pagosdigitales.com/Website/Servicios/ConsultarSaldo/9a7bbd8b-c817-4071-9b60-1831dc2f3d4a"
        self.post_url = "https://www.pagosdigitales.com/Website/Gestopagos/ConsultarSaldo"
        self.session = requests.Session()
        # Headers extraídos de tus logs [cite: 4, 5, 6]
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
            # Necesario para que el servidor acepte nuestra petición posterior
            response_get = self.session.get(self.base_url)
            if response_get.status_code != 200:
                return {"error": "Error al cargar página de inicio"}

            soup = BeautifulSoup(response_get.text, 'html.parser')
            # Buscamos el token oculto [cite: 20]
            token_input = soup.find('input', {'name': '__RequestVerificationToken'})
            if not token_input:
                return {"error": "Token de seguridad no encontrado"}
            
            token = token_input['value']

            # PASO 2: Enviar los datos (POST)
            # Parámetros extraídos de PDADEUDO.txt [cite: 17-20]
            payload = {
                "id": "9a7bbd8b-c817-4071-9b60-1831dc2f3d4a",
                "hRef": "nulo",
                "fuente": "",
                "Referencia": referencia,
                "__RequestVerificationToken": token
            }

            response_post = self.session.post(self.post_url, data=payload)

            # PASO 3: Analizar la respuesta
            # Caso SIN DEUDA: En PDSINADEUDO.txt vemos que redirige o muestra el error 
            if "Referencia sin adeudo" in response_post.text or "Referencia sin adeudo" in response_post.url:
                return {
                    "estatus": "PAGADO",
                    "monto": 0
                }
            
            # Caso CON DEUDA: En PDADEUDO.txt vemos el resumen y el monto 
            soup_res = BeautifulSoup(response_post.text, 'html.parser')
            
            # Buscamos el div que contiene el precio. Según tu archivo es un div con border-info
            divs_info = soup_res.find_all("div", class_="border-info")
            monto_encontrado = "$0.00"
            
            for div in divs_info:
                texto = div.get_text(strip=True)
                if "$" in texto:
                    monto_encontrado = texto
                    break
            
            # Si encontramos el símbolo de peso, asumimos que es el cobro
            if "$" in monto_encontrado:
                return {
                    "estatus": "DEUDA",
                    "monto": monto_encontrado
                }
            else:
                # Si llegamos aquí, algo raro pasó (ni pagado ni deuda clara)
                return {"error": "Respuesta desconocida"}

        except Exception as e:
            return {"error": str(e)}
