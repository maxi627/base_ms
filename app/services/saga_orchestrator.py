


#TODO: ver el limiter y agregarlo al principio (probar  con 50 peticiones por segundo)
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests
import logging
from response_message import ResponseBuilder
from typing import List

app = Flask(__name__)

# Crear Limiter sin 'key_func' al inicio
limiter = Limiter(key_func=get_remote_address)

# Inicializar Limiter con la app
limiter.init_app(app)

# Configurar Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@limiter.limit("50 per second")
def hacer_peticion_limited(url, data):
    """Realiza una petición HTTP POST con limitación de tasa."""
    try:
        response = requests.post(url, json=data)
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
    def __init__(self, actions: List[Action], data):
        self.actions = actions
        self.data = data
        self.IDs = []
        self.response = ResponseBuilder()

    def execute(self):
        """Ejecuta la saga en orden y maneja la compensación en caso de fallo."""
        self.response.add_status_code(201).add_message("OK").add_data({"message": "Operación realizada con éxito"})
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
                    response = hacer_peticion_limited(url, datos_a_enviar)
        
                if response.status_code == 201:
                    logger.info(f"ID generado: {id_generado}")
                else:
                    self.response.add_status_code(response.status_code) \
                                 .add_message(response.json().get('message')) \
                                 .add_data(response.json().get('data'))
                    self.compensate(index)
                    break
                
            except Exception as e:
                self.response.add_status_code(500).add_message("Error durante la ejecución de la saga").add_data({"error": str(e)})
                self.compensate(index)
                break
            
                    
        logger.debug(f"Estado final de IDs: {self.IDs}")
        return self.response.build()

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
