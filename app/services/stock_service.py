import logging
import requests
from flask import current_app
from app import retry_logic  # Importar la lógica de retry
from app import obtener_circuit_breaker  # Importar el circuito breaker
# Configuración del logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Obtener el objeto de CircuitBreaker
circuit_breaker = obtener_circuit_breaker()


class StockService:
    """
    Servicio para interactuar con el sistema de stock externo.
    """

    @retry_logic
    @circuit_breaker
    def agregar_stock(self, data):
        """
        Agrega stock mediante una solicitud al servicio externo con reintentos.
        :param data: Diccionario con los datos del stock.
        :return: Respuesta JSON del servicio de stock y la URL.
        :raises Exception: Si ocurre un error en la solicitud.
        """
        logger.info("Intentando agregar stock: %s", data)

        try:
            data_stock = data.get('stock')
            response = requests.post(
                current_app.config['STOCK_URL'],
                json=data_stock,
                verify=False  # Cambiar a True y configurar certificados en producción.
            )
            response.raise_for_status()

            logger.info("Stock agregado con éxito. Respuesta: %s", response.json())
            return current_app.config['STOCK_URL'], response.json()

        except requests.RequestException as e:
            logger.warning("Fallo al agregar stock. Lanzando reintento...")
            raise

    @retry_logic
    @circuit_breaker
    def borrar_stock(self, id_stock):
        """
        Elimina un stock mediante una solicitud al servicio externo.
        :param id_stock: ID del stock a eliminar.
        :return: True si el stock fue eliminado, False si no se encontró.
        :raises Exception: Si ocurre un error en la solicitud.
        """
        intento_actual = getattr(self.borrar_stock, "retry.statistics", {}).get("attempt_number", 1)
        logger.info(f"[Intento {intento_actual}/3] Enviando solicitud para eliminar stock con ID: {id_stock}")

        try:
            response = requests.delete(
                f"{current_app.config['STOCK_URL']}/{id_stock}",
                verify=False  # Cambiar a True y configurar certificados en producción.
            )

            if response.status_code == 404:
                logger.warning("Stock con ID %s no encontrado.", id_stock)
                return False

            response.raise_for_status()
            logger.info("Stock con ID %s eliminado con éxito.", id_stock)
            return True

        except requests.RequestException as e:
            logger.exception("Error al eliminar stock con ID %s.", id_stock)
            raise Exception(f"Error al eliminar stock con ID {id_stock}: {str(e)}")

    @retry_logic
    @circuit_breaker
    def revertir_stock(self, producto_id, cantidad):
        """
        Reintegra stock en caso de fallo en la saga.
        """
        try:
            logger.info(f"Reintegrando {cantidad} unidades al producto {producto_id}")

            response = requests.put(
                f"{current_app.config['STOCK_URL']}/revertir",
                json={"producto_id": producto_id, "cantidad": cantidad},
                verify=False
            )

            if response.status_code == 200:
                logger.info(f"Stock reintegrado para producto {producto_id}")
                return response.json()
            else:
                raise Exception(f"Error al revertir stock: {response.status_code} - {response.text}")

        except requests.RequestException as e:
            logger.exception(f"Error al revertir stock del producto {producto_id}.")
            raise
