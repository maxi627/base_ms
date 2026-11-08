import logging
from flask import current_app
from app import retry_logic  # Importar la lógica de retry
from app import obtener_circuit_breaker  # Importar el circuito breaker
from app.services.stock_service import StockService
import requests
# Configurar logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Obtener el objeto de CircuitBreaker
circuit_breaker = obtener_circuit_breaker("producto")

class ProductoService:
    @retry_logic
    @circuit_breaker
    def obtener_producto(self, producto_id):
        """
        Obtiene información de un producto por su ID.
        :return: Diccionario con el producto (campo 'data' de la respuesta) o None si no existe.
        """
        try:
            url = f"{current_app.config['PRODUCTO_URL']}/{producto_id}"
            logger.info(f"Obteniendo producto: {producto_id}")

            response = requests.get(url, verify=False)
            if response.status_code == 200:
                return response.json().get("data")
            elif response.status_code == 404:
                logger.warning(f"Producto con ID {producto_id} no encontrado.")
                return None
            else:
                raise Exception(f"Error inesperado: {response.status_code} - {response.text}")

        except requests.RequestException as e:
            logger.exception("Error al obtener el producto.")
            raise

    def validar_disponibilidad(self, producto_id, cantidad):
        """
        Verifica si un producto existe, está activado y tiene stock suficiente.
        El stock no está en ms_producto: se calcula con los movimientos de ms_stock.
        :param producto_id: ID del producto a verificar.
        :param cantidad: Cantidad requerida del producto.
        :return: True si se puede vender esa cantidad, False en caso contrario.
        """
        logger.info(f"Validando disponibilidad de producto {producto_id} para {cantidad} unidades.")

        producto = self.obtener_producto(producto_id)
        if not producto:
            return False
        if not producto.get("activado", False):
            logger.warning(f"Producto {producto_id} no está activado.")
            return False

        stock_disponible = StockService().obtener_disponible(producto_id)
        if stock_disponible >= cantidad:
            logger.info(f"Producto {producto_id} tiene stock suficiente ({stock_disponible} disponibles).")
            return True

        logger.warning(f"Producto {producto_id} no tiene stock suficiente ({stock_disponible} disponibles).")
        return False
