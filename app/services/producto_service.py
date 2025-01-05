import logging
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from app import cache
from app.services.stock_service import StockService

# Configuración del logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ProductoService:
    """
    Servicio para consultar información de productos, utilizando caché y el servicio de stock.
    """

    def __init__(self):
        self.stock_service = StockService()

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_fixed(1),  # Espera fija de 1 segundo entre intentos
        stop=stop_after_attempt(3),  # Máximo 3 intentos
        reraise=True
    )
    def consultar_producto(self, id_producto: int):
        """
        Consulta la información de un producto.
        Prioriza el uso de caché, y si no está disponible, realiza una solicitud al servicio de stock.
        :param id_producto: ID del producto a consultar.
        :return: Datos del producto si se encuentra.
        :raises Exception: Si ocurre un error durante la consulta.
        """
        try:
            logger.info("Consultando producto con ID: %s", id_producto)

            # Verificar si el producto está en caché
            producto = cache.get(f"producto_{id_producto}")
            if producto:
                logger.info("Producto con ID %s encontrado en caché.", id_producto)
                return producto

            # Obtener el producto desde el servicio de stock
            logger.info("Producto con ID %s no está en caché. Consultando en el servicio de stock...", id_producto)
            producto = self.stock_service.obtener_producto(id_producto)

            if producto is None:
                logger.warning("Producto con ID %s no encontrado en el servicio de stock.", id_producto)
                return None

            # Guardar el producto en caché con un tiempo de expiración
            cache.set(f"producto_{id_producto}", producto, timeout=100)
            logger.info("Producto con ID %s almacenado en caché.", id_producto)

            return producto

        except Exception as e:
            logger.exception("Error al consultar producto con ID %s.", id_producto)
            raise Exception(f"Error al consultar producto con ID {id_producto}: {e}")
