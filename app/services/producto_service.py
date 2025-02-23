import logging
from flask import current_app
from app import retry_logic  # Importar la lógica de retry
from app import obtener_circuit_breaker  # Importar el circuito breaker
import requests
# Configurar logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Obtener el objeto de CircuitBreaker
circuit_breaker = obtener_circuit_breaker()

class ProductoService:
    @retry_logic
    @circuit_breaker
    def obtener_producto(self, producto_id):
        """
        Obtiene información de un producto por su ID.
        """
        try:
            url = f"{current_app.config['PRODUCTO_URL']}/{producto_id}"
            logger.info(f"Obteniendo producto: {producto_id}")

            response = requests.get(url, verify=False)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"Producto con ID {producto_id} no encontrado.")
                return None
            else:
                raise Exception(f"Error inesperado: {response.status_code} - {response.text}")

        except requests.RequestException as e:
            logger.exception("Error al obtener el producto.")
            raise

    @retry_logic
    @circuit_breaker
    def validar_disponibilidad(self, producto_id, cantidad):
        """
        Verifica si hay suficiente stock de un producto antes de realizar una compra.
        :param producto_id: ID del producto a verificar.
        :param cantidad: Cantidad requerida del producto.
        :return: True si hay suficiente stock, False si no hay suficiente stock.
        :raises Exception: Si ocurre un error en la solicitud.
        """
        try:
            url = f"{current_app.config['PRODUCTO_URL']}/{producto_id}"
            logger.info(f"Validando disponibilidad de producto {producto_id} para {cantidad} unidades.")

            response = requests.get(url, verify=False)

            if response.status_code == 200:
                producto = response.json()
                stock_disponible = producto.get("stock", 0)
                if stock_disponible >= cantidad:
                    logger.info(f"Producto {producto_id} tiene stock suficiente ({stock_disponible} disponibles).")
                    return True
                else:
                    logger.warning(f"Producto {producto_id} no tiene stock suficiente ({stock_disponible} disponibles).")
                    return False
            elif response.status_code == 404:
                logger.warning(f"Producto con ID {producto_id} no encontrado.")
                return False
            else:
                raise Exception(f"Error inesperado: {response.status_code} - {response.text}")

        except requests.RequestException as e:
            logger.exception(f"Error al validar disponibilidad del producto {producto_id}.")
            raise
