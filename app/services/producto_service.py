from . import CatalogoService, CompraService, PagoService, InventarioService, SagaBuilder
from app import cache

catalogo_service = CatalogoService()
compra_service = CompraService()
pago_service = PagoService()
inventario_service = InventarioService()

class ProductoService:

    def consultar_producto(self, id_producto: int):
        try:
            # Verificar si el producto está en caché
            producto = cache.get(f"producto_{id_producto}")
            if producto is None:
                # Obtener el producto del servicio de catálogo
                producto = catalogo_service.obtener_producto(id_producto)
                if producto is None:
                    return None
                # Serializar y almacenar el producto en caché
                cache.set(f"producto_{id_producto}", producto, timeout=100)
            return producto
        except Exception as e:
            raise Exception(f"Error fetching producto with id {id_producto}: {e}")
