


#TODO: ver el limiter y agregarlo al principio (probar  con 50 peticiones por segundo)
import logging
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type, before_sleep_log
import requests
from flask import Flask

# Crear app de Flask
app = Flask(__name__)

# Configurar Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Cambiar a INFO para menos verbosidad
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Configuración para los reintentos con Tenacity
@retry(
    retry=retry_if_exception_type(requests.RequestException),
    wait=wait_fixed(2),  # Espera 2 segundos entre intentos
    stop=stop_after_attempt(3),  # Máximo 3 intentos
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.INFO)  # Mostrar reintentos como INFO
)
def hacer_peticion(url, data):
    """Realiza una petición HTTP POST con reintentos."""  
    try:
        logger.info(f"Enviando petición a {url} con datos: {data}")
        response = requests.post(url, json=data)
        response.raise_for_status()  # Lanza error si falla
        return response
    except requests.RequestException as e:
        logger.error(f"Error en la petición a {url}: {e}")
        raise

class Action:
    """Define una acción en la Saga, con su ejecución y compensación."""
    def __init__(self, execute_fn, compensate_fn):
        self.execute_fn = execute_fn
        self.compensate_fn = compensate_fn
        self.url = None

    def execute(self, data):
        """Ejecuta la acción llamando al microservicio correspondiente."""
        url, response_data = self.execute_fn(data)
        self.url = url
        return url, response_data

    def compensate(self, id):
        """Compensa la acción eliminando el recurso creado."""
        return self.compensate_fn(id)

class Saga:
    """Orquestador de la saga: ejecuta y compensa si falla."""
    def __init__(self, actions, data):
        self.actions = actions
        self.data = data
        self.IDs = []
        self.response = {"message": "OK", "status_code": 201, "data": {"message": "Operación realizada con éxito"}}

    def execute(self):
        """Ejecuta la saga en orden y maneja la compensación en caso de fallo."""
        saga_data = self.data.copy()

        for index, action in enumerate(self.actions):
            try:
                url, response_data = action.execute(saga_data)
        
                datos_relevantes = response_data.get("data", {}).copy()
                logger.info(f"Datos relevantes: {datos_relevantes}")
                id_generado = datos_relevantes.pop("id", None)
                logger.info(f"ID generado: {id_generado}")
                self.IDs.append(id_generado)
        
                # Determinar qué datos enviar
                if index == 0:  # PagoService espera datos de pago
                    datos_a_enviar = saga_data["pago"]
                elif index == 1:  # CompraService espera datos de compra
                    datos_a_enviar = saga_data["compra"]
                elif index == 2:  # StockService espera datos de stock
                    datos_a_enviar = saga_data["stock"]
        
                with app.test_request_context():
                    response = hacer_peticion(url, datos_a_enviar)
        
                if response.status_code == 201:
                    logger.info(f"ID generado: {id_generado}")
                else:
                    self.response["status_code"] = response.status_code
                    self.response["message"] = response.json().get('message')
                    self.response["data"] = response.json().get('data')
                    self.compensate(index)
                    break
                
            except Exception as e:
                self.response["status_code"] = 500
                self.response["message"] = "Error durante la ejecución de la saga"
                self.response["data"] = {"error": str(e)}
                self.compensate(index)
                break
        
        logger.info(f"Estado final de IDs: {self.IDs}")
        return self.response

    def compensate(self, index):
        """Compensa todas las acciones previas en orden inverso"""
        try:
            for i in range(index - 1, -1, -1):  # Ir de index-1 hasta 0
                action = self.actions[i]
                if i < len(self.IDs) and self.IDs[i] is not None:
                    url_compensacion = f"{action.url}/{self.IDs[i]}"
                    response = requests.delete(url_compensacion)
                    logger.info(f"Compensación realizada en {url_compensacion}: {response.status_code}")
                else:
                    logger.warning(f"No hay ID disponible para compensar en el índice {i}")

        except Exception as e:
            logger.exception(f"Error en la compensación: {e}")

if __name__ == "__main__":
    app.run(debug=True)