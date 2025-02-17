import logging
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type, before_sleep_log
from flask import current_app

# Configuración del logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class StockService:
    """
    Servicio para interactuar con el sistema de stock externo.
    """

    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        wait=wait_fixed(2),  # Espera fija de 2 segundos entre intentos
        stop=stop_after_attempt(3),  # Máximo 3 intentos
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.WARNING)  # Log antes de cada reintento
    )
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

    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        wait=wait_fixed(2),  # Espera fija de 2 segundos entre intentos
        stop=stop_after_attempt(3),  # Máximo 3 intentos
        reraise=True
    )
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
