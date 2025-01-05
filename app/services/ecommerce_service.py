
  #TODO: verificar el estatus code que devuelve para ver si se compensa o no.

            #TODO: obtener por cache el stock de ese producto, si es mayor que cero, sino compensar


import requests
import logging
from tenacity import retry, stop_after_attempt, wait_random, retry_if_exception_type
from flask import current_app

# Configuración del logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class StockService:
    """
    Servicio para interactuar con el microservicio de stock.
    """

    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        wait=wait_random(min=1, max=2),
        stop=stop_after_attempt(3),
        reraise=True
    )
    def obtener_producto(self, id_producto):
        """
        Obtiene la información de un producto por su ID desde el servicio de stock.
        Implementa reintentos con tenacity para manejar errores transitorios.
        :param id_producto: ID del producto a buscar.
        :return: Datos del producto si se encuentra.
        :raises Exception: Si ocurre un error en la solicitud.
        """
        try:
            logger.info("Intentando obtener información del producto con ID: %s", id_producto)

            response = requests.get(
                f"{current_app.config['STOCK_URL']}/{id_producto}",
                verify=False  # Cambiar a True y configurar certificados en producción.
            )

            # Manejo de respuestas específicas
            if response.status_code == 404:
                logger.warning("Producto con ID %s no encontrado.", id_producto)
                return None

            response.raise_for_status()
            producto = response.json()

            # Validación del stock
            stock = producto.get('stock', 0)
            if stock <= 0:
                logger.warning("El producto con ID %s no tiene stock suficiente.", id_producto)
                raise Exception(f"El producto con ID {id_producto} no tiene stock disponible.")

            logger.info("Información del producto obtenida exitosamente: %s", producto)
            return producto

        except requests.RequestException as e:
            logger.exception("Error al obtener el producto con ID %s.", id_producto)
            raise Exception(f"Error al obtener el producto con ID {id_producto}: {str(e)}")
