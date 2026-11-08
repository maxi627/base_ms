import requests
import logging
from flask import current_app
from app import retry_logic  # Importar la lógica de retry
from app import obtener_circuit_breaker  # Importar el circuito breaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Obtener el objeto de CircuitBreaker
circuit_breaker = obtener_circuit_breaker("pagos")

class PagoService:
    def agregar_pago(self, data):
        """
        Registra un pago en ms_pagos.
        :param data: Diccionario de la saga; se usa data['pago'].
        :return: (URL del servicio, Respuesta JSON del servicio de pagos).
        """
        data_pago = data.get('pago')
        logger.info("Enviando solicitud para agregar un pago: %s", data_pago)
        # El retry y el circuit breaker se aplican solo en _realizar_pago,
        # para no anidar reintentos (3 x 3 intentos).
        return self._realizar_pago(data_pago)

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
            error_details = response.json().get('data', 'No especificado')
            logger.error("Datos inválidos: %s", error_details)
            raise Exception(f"Datos inválidos: {error_details}")
        else:
            logger.error("Error inesperado: %s - %s", response.status_code, response.text)
            raise Exception(f"Error inesperado: {response.status_code} - {response.text}")

    @retry_logic
    @circuit_breaker
    def borrar_pago(self, id_pago):
        """
        Elimina un pago en ms_pagos (compensación de la saga).
        :param id_pago: ID del pago a borrar.
        :return: True si el pago fue eliminado, False si no se encontró.
        :raises Exception: Si el servicio responde con un error inesperado.
        """
        try:
            logger.info("Iniciando la eliminación del pago con ID: %s", id_pago)
            response = requests.delete(
                f"{current_app.config['PAGOS_URL']}/{id_pago}",
                verify=False  # Cambiar a True en producción
            )

            if response.status_code == 404:
                logger.warning("Pago con ID %s no encontrado.", id_pago)
                return False
            elif response.status_code in (200, 204):
                logger.info("Pago con ID %s eliminado con éxito.", id_pago)
                return True
            else:
                logger.error("Error inesperado al borrar el pago: %s - %s", response.status_code, response.text)
                raise Exception(f"Error inesperado al borrar el pago: {response.status_code} - {response.text}")

        except requests.RequestException:
            # Se relanza tal cual para que retry_logic pueda reintentar.
            logger.exception("Error de red al borrar el pago con ID %s.", id_pago)
            raise
