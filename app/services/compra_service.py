
#TODO: aplicar retry

#TODO: verificar el estatus code que devuelve para ver si se compensa o no.

import requests
import logging
from flask import current_app
from app import retry_logic  # Importar la lógica de retry
from app import obtener_circuit_breaker  # Importar el circuito breaker

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,  # Cambia a DEBUG para mayor detalle
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)  # Logger específico para este módulo

# Obtener el objeto de CircuitBreaker
circuit_breaker = obtener_circuit_breaker()

class CompraService:
    """
    Servicio para interactuar con el microservicio de compras.
    """

    @retry_logic
    @circuit_breaker
    def comprar(self, data):
        """
        Realiza una compra enviando una solicitud POST al servicio de compras.
        :param data: Diccionario con los datos de la compra.
        :return: (URL del servicio, Respuesta JSON del servicio de compras).
        :raises Exception: Si ocurre un error en la solicitud.
        """
        try:
            logger.info("Iniciando el proceso de compra con datos: %s", data)
            data_compra = data.get('compra')
            url = current_app.config['COMPRAS_URL']
            response = requests.post(
                url,
                json=data_compra,
                verify=False  # Cambiar a True en producción
            )
    
            if response.status_code == 201:
                logger.info("Compra realizada con éxito: %s", response.json())
                return url, response.json()  # <--- Devuelve la URL también
            elif response.status_code == 409:
                logger.warning("Conflicto: la compra ya existe.")
                raise Exception("Compra ya existe (conflicto).")
            elif response.status_code == 422:
                logger.warning("Datos inválidos enviados: %s", response.json())
                raise Exception(f"Datos inválidos: {response.json().get('errors', 'No especificado')}")
            else:
                logger.error("Error inesperado: %s - %s", response.status_code, response.text)
                raise Exception(f"Error inesperado: {response.status_code} - {response.text}")
    
        except requests.RequestException as e:
            logger.exception("Error de red durante la compra.")
            raise Exception(f"Error al realizar la compra: {str(e)}")


    @retry_logic
    @circuit_breaker
    def borrar_compra(self, id_compra):
        """
        Envía una solicitud DELETE al servicio de compras para borrar una compra específica.
        :param id_compra: ID de la compra a borrar.
        :return: True si la compra fue eliminada, False si no se encontró.
        :raises Exception: Si ocurre un error en la solicitud.
        """
        try:
            logger.info("Iniciando la eliminación de la compra con ID: %s", id_compra)
            response = requests.delete(
                f"{current_app.config['COMPRAS_URL']}/{id_compra}",
                verify=False  # Cambiar a True en producción
            )

            if response.status_code == 404:
                logger.warning("Compra con ID %s no encontrada.", id_compra)
                return False
            elif response.status_code == 204:
                logger.info("Compra con ID %s eliminada con éxito.", id_compra)
                return True
            else:
                logger.error("Error inesperado al borrar la compra: %s - %s", response.status_code, response.text)
                raise Exception(f"Error inesperado al borrar la compra: {response.status_code} - {response.text}")

        except requests.RequestException as e:
            logger.exception("Error de red al borrar la compra con ID %s.", id_compra)
            raise Exception(f"Error al borrar la compra con ID {id_compra}: {str(e)}")
