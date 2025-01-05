
#TODO: Servicios instanciados globalmente, que pasa sí un hilo se utiliza antes de cerrarse la petición
import logging
from app.services.saga_orchestrator import SagaBuilder
from app.services import PagoService, CompraService, StockService

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Clases de acciones con servicios instanciados dentro de ellas
class AgregarPagoAction:
    @staticmethod
    def action(data):
        try:
            logger.info("Iniciando acción de agregar pago.")
            pago_service = PagoService()  # Instanciar el servicio dentro de la acción
            return pago_service.agregar_pago(data)
        except Exception as e:
            logger.error(f"Error en agregar pago: {e}")
            raise

    @staticmethod
    def compensation(id_pago):
        try:
            logger.info(f"Iniciando compensación de agregar pago con id: {id_pago}")
            pago_service = PagoService()
            return pago_service.borrar_pago(id_pago)
        except Exception as e:
            logger.error(f"Error en compensación de pago: {e}")
            raise

class CrearCompraAction:
    @staticmethod
    def action(data):
        try:
            logger.info("Iniciando acción de crear compra.")
            compra_service = CompraService()  # Instanciar el servicio dentro de la acción
            return compra_service.comprar(data)
        except Exception as e:
            logger.error(f"Error en crear compra: {e}")
            raise

    @staticmethod
    def compensation(id_compra):
        try:
            logger.info(f"Iniciando compensación de compra con id: {id_compra}")
            compra_service = CompraService()
            return compra_service.borrar_compra(id_compra)
        except Exception as e:
            logger.error(f"Error en compensación de compra: {e}")
            raise

class AgregarStockAction:
    @staticmethod
    def action(data):
        try:
            logger.info("Iniciando acción de agregar stock.")
            stock_service = StockService()  # Instanciar el servicio dentro de la acción
            return stock_service.agregar_stock(data)
        except Exception as e:
            logger.error(f"Error en agregar stock: {e}")
            raise

    @staticmethod
    def compensation(id_stock):
        try:
            logger.info(f"Iniciando compensación de agregar stock con id: {id_stock}")
            stock_service = StockService()
            return stock_service.borrar_stock(id_stock)
        except Exception as e:
            logger.error(f"Error en compensación de stock: {e}")
            raise

# Construcción de la Saga usando SagaBuilder
saga_builder = SagaBuilder()

# Añadir acciones a la Saga
saga_builder.action(
    action=AgregarPagoAction.action,
    compensation=AgregarPagoAction.compensation
)

saga_builder.action(
    action=CrearCompraAction.action,
    compensation=CrearCompraAction.compensation
)

saga_builder.action(
    action=AgregarStockAction.action,
    compensation=AgregarStockAction.compensation
)

# Configurar los datos para la saga
saga = saga_builder.set_data({
    "pago": {"monto": 100, "metodo": "tarjeta"},
    "compra": {"producto_id": 1, "cantidad": 2},
    "stock": {"producto_id": 1, "cantidad": -2}
}).build()

# Ejecutar la saga
response = saga.execute()
logger.info(f"Respuesta final de la saga: {response}")
