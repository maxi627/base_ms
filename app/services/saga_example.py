from app.services.saga_orchestrator import SagaBuilder
saga_builder = SagaBuilder()

# Acción de agregar pago
saga_builder.action(
    action=lambda data: pago_service.agregar_pago(data),
    compensation=lambda id_pago: pago_service.borrar_pago(id_pago)
)

# Acción de crear compra
saga_builder.action(
    action=lambda data: compra_service.comprar(data),
    compensation=lambda id_compra: compra_service.borrar_compra(id_compra)
)

# Acción de agregar stock
saga_builder.action(
    action=lambda data: stock_service.agregar_stock(data),
    compensation=lambda id_stock: stock_service.borrar_stock(id_stock)
)

# Configurar los datos para la saga
saga = saga_builder.set_data({
    "pago": {"monto": 100, "metodo": "tarjeta"},
    "compra": {"producto_id": 1, "cantidad": 2},
    "stock": {"producto_id": 1, "cantidad": -2}
}).build()

# Ejecutar la saga
response = saga.execute()
print(response)
