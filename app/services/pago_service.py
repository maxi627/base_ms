
# TODO: verificar el estatus code que devuelve para ver si se compensa o no.
import requests
import logging
from flask import current_app
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from app import retry_logic  # Importar la lógica de retry
from app import obtener_circuit_breaker  # Importar el circuito breaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Obtener el objeto de CircuitBreaker
circuit_breaker = obtener_circuit_breaker()

class PagoService:
    @retry_logic
    @circuit_breaker
    def agregar_pago(self, data):
        try:
            data_pago = data.get('pago')
            logger.info("Enviando solicitud para agregar un pago: %s", data_pago)

            with current_app.app_context():  # Asegura que hay un contexto de aplicación
                return self._realizar_pago(data_pago)

        except requests.RequestException as e:
            logger.exception("Error al agregar el pago.")
            raise

    @retry_logic
    @circuit_breaker
    def _realizar_pago(self, data_pago):
        url = current_app.config['PAGOS_URL']
        response = requests.post(url, json=data_pago, verify=False)

        logger.info("Respuesta del servicio de pagos: %s", response.status_code)

        if response.status_code == 201:
            logger.info("Pago creado exitosamente.")
            return url, response.json()  # Devolver URL y el data de la respuesta
        elif response.status_code == 409:
            logger.warning("Pago ya existe (conflicto).")
            raise Exception("Pago ya existe (conflicto).")
        elif response.status_code == 422:
            error_details = response.json().get('errors', 'No especificado')
            logger.error("Datos inválidos: %s", error_details)
            raise Exception(f"Datos inválidos: {error_details}")
        else:
            logger.error("Error inesperado: %s - %s", response.status_code, response.text)
            raise Exception(f"Error inesperado: {response.status_code} - {response.text}")
