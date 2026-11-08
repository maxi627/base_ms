# base_ms

Repositorio **base** del e-commerce basado en microservicios. Cumple dos funciones:

1. **Base de datos compartida:** levanta el contenedor PostgreSQL `ecomercedb` que usan todos los microservicios.
2. **Orquestador Saga:** coordina una compra distribuida entre [ms_pagos](https://github.com/maxi627/ms_pagos), [ms_compra](https://github.com/maxi627/ms_compra) y [ms_stock](https://github.com/maxi627/ms_stock), con compensaciones si algún paso falla, más **retry** y **circuit breaker** en cada llamada HTTP.

- **Stack:** Python · Flask · SQLAlchemy · PostgreSQL 15.6 · Redis · `requests` · `tenacity` (retry) · `pybreaker` (circuit breaker) · Docker

---

## Ecosistema

Este repositorio forma parte de un conjunto de repos que funcionan juntos:

| Repositorio | Rol | Puerto | Host vía Traefik |
|---|---|---|---|
| [servicios](https://github.com/maxi627/servicios) | Infraestructura: Traefik (API gateway) y Redis | 80 / 443 / 8080 · 6379 | — |
| **[base_ms](https://github.com/maxi627/base_ms)** (este repo) | PostgreSQL compartida (`ecomercedb`) + orquestador Saga | 5432 · 5005 | — |
| [ms_producto](https://github.com/maxi627/ms_producto) | Catálogo de productos | 5003 | `producto.localhost` |
| [ms_stock](https://github.com/maxi627/ms_stock) | Movimientos de inventario | 5001 | `stock.localhost` |
| [ms_pagos](https://github.com/maxi627/ms_pagos) | Registro de pagos | 5002 | `pagos.localhost` |
| [ms_compra](https://github.com/maxi627/ms_compra) | Registro de compras | 5000 | `compras.localhost` |

```mermaid
flowchart LR
    cliente([Cliente]) -->|HTTP :80| traefik
    saga[base_ms<br/>Orquestador Saga] -->|HTTP| traefik
    traefik{{Traefik}} -->|compras.localhost| compra[ms_compra :5000]
    traefik -->|stock.localhost| stock[ms_stock :5001]
    traefik -->|pagos.localhost| pagos[ms_pagos :5002]
    traefik -->|producto.localhost| producto[ms_producto :5003]
    compra & stock & pagos & producto --> pg[(PostgreSQL<br/>ecomercedb)]
    compra & stock & pagos & producto --> redis[(Redis)]
```

Todos los contenedores se comunican por la red Docker externa **`red1`**.

### Levantar todo el ecosistema

```bash
# 1. Red compartida (una sola vez)
docker network create red1

# 2. Infraestructura: Redis y Traefik
cd servicios
docker compose -f docker-compose.redis.yml up -d
docker compose -f docker-compose.traefik.yml up -d

# 3. Base de datos PostgreSQL (este repo)
cd ../base_ms
docker compose up -d

# 4. Microservicios (cada uno con su propio .env)
cd ../ms_producto && docker compose -f docker-compose.producto.yml up -d --build
cd ../ms_stock    && docker compose -f docker-compose.stock.yml up -d --build
cd ../ms_pagos    && docker compose -f docker-compose.pagos.yml up -d --build
cd ../ms_compra   && docker compose -f docker-compose.compra.yml up -d --build
```

Dashboard de Traefik: <http://localhost:8080>. Si los hosts `*.localhost` no resuelven en tu sistema, agregalos al archivo `hosts` apuntando a `127.0.0.1`.

---

## Base de datos

`docker-compose.yml` levanta **PostgreSQL 15.6** con:

- Contenedor `ecomercedb`: es el host que usan los microservicios en sus `DATABASE_URI`.
- Puerto `5432` expuesto al host (útil para los tests locales).
- Volumen `postgres_data` para persistir los datos.
- Conexión a la red externa `red1`.

Cada microservicio crea sus propias tablas (`Compra`, `Pagos`, `stock`, `producto`) al arrancar, con `db.create_all()`.

## Saga de compra

Una compra toca tres servicios. Como no hay transacción distribuida, se usa el **patrón Saga orquestado**: cada paso tiene una acción y una compensación, y si un paso falla se deshacen los anteriores en orden inverso.

```mermaid
sequenceDiagram
    participant S as Saga (base_ms)
    participant P as ms_pagos
    participant C as ms_compra
    participant ST as ms_stock

    S->>P: POST /pagos
    P-->>S: 201 {id_pago}
    S->>C: POST /compras
    C-->>S: 201 {id_compra}
    S->>ST: POST /stock
    alt todo OK
        ST-->>S: 201 {id_stock}
        Note over S: Respuesta 201 "Operación realizada con éxito"
    else falla un paso
        ST--xS: error
        S->>C: DELETE /compras/{id_compra}
        S->>P: DELETE /pagos/{id_pago}
        Note over S: Respuesta con el error y status del paso que falló
    end
```

| Paso | Acción | Compensación |
|---|---|---|
| 1 | `PagoService.agregar_pago` → `POST {PAGOS_URL}` | `DELETE {PAGOS_URL}/{id}` |
| 2 | `CompraService.comprar` → `POST {COMPRAS_URL}` | `DELETE {COMPRAS_URL}/{id}` |
| 3 | `StockService.agregar_stock` → `POST {STOCK_URL}` | `DELETE {STOCK_URL}/{id}` |

Además, `ProductoService` permite obtener un producto (`GET {PRODUCTO_URL}/{id}`) y `StockService.revertir_stock` permite reintegrar unidades.

### Código

```
app/
├── __init__.py                  # create_app, Redis, circuit breaker global y retry_logic
├── config/                      # Configuración por entorno y URLs de los microservicios
└── services/
    ├── saga_orchestrator.py     # Clases Action (ejecutar / compensar) y Saga (orquestador)
    ├── saga_example_arreglado.py# Ejemplo de ejecución de la Saga de compra
    ├── pago_service.py          # Cliente HTTP de ms_pagos
    ├── compra_service.py        # Cliente HTTP de ms_compra
    ├── stock_service.py         # Cliente HTTP de ms_stock
    ├── producto_service.py      # Cliente HTTP de ms_producto
    └── response_message.py      # ResponseMessage / ResponseBuilder
docker-compose.yml               # PostgreSQL ecomercedb
main.py                          # App Flask mínima en el puerto 5005 para pruebas locales
```

### Resiliencia

| Mecanismo | Librería | Configuración |
|---|---|---|
| Retry | `tenacity` | 3 intentos, espera exponencial entre 2 y 10 s, solo ante `requests.RequestException` |
| Circuit breaker | `pybreaker` | Se abre después de 3 fallos seguidos y se vuelve a probar a los 30 s. Una sola instancia compartida por todos los clientes |
| Rate limiting | (en cada microservicio) | Flask-Limiter con Redis como backend |

## Configuración

Crear un archivo `.env` en la raíz del repo:

```env
FLASK_ENV=development

# PostgreSQL (usado por docker-compose.yml)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=ecomerce
POSTGRES_PORT=5432
DEV_DATABASE_URI=postgresql://postgres:postgres@localhost:5432/ecomerce
TEST_DB_URI=postgresql://postgres:postgres@localhost:5432/ecomerce_test
PROD_DATABASE_URI=postgresql://postgres:postgres@localhost:5432/ecomerce

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=cambiar
REDIS_DB=0

# Endpoints de los microservicios (vía Traefik)
PAGOS_URL=http://pagos.localhost/api/v1/pagos
COMPRAS_URL=http://compras.localhost/api/v1/compras
STOCK_URL=http://stock.localhost/api/v1/stock
PRODUCTO_URL=http://producto.localhost/api/v1/producto
```

> Los mismos valores de `POSTGRES_*` tienen que estar en el `.env` de cada microservicio.

## Ejecución

```bash
# Base de datos
docker compose up -d

# Orquestador (local, con el resto del ecosistema levantado)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt requests

# Ejecutar la Saga de ejemplo (desde la raíz del repo)
python -m app.services.saga_example_arreglado
```

`requests` se instala aparte porque todavía no figura en `requirements.txt`.

El ejemplo envía estos datos:

```json
{
  "pago":   { "precio": 100, "medio_pago": "tarjeta de credito", "producto_id": 1 },
  "compra": { "producto_id": 1, "fecha_compra": "2025-01-23T10:00:00", "direccion_envio": "Calle 123" },
  "stock":  { "producto_id": 1, "cantidad": 10, "entrada_salida": 1, "fecha_transaccion": "2025-01-23T10:00:00" }
}
```

Si Python no encuentra el módulo `app`, agregar la raíz del repo al `PYTHONPATH` (`set PYTHONPATH=<ruta del repo>` en Windows).

## Pendientes

- Mover el circuit breaker a la configuración de Traefik (middleware en los compose) en lugar de usarlo como librería.
- Agregar `PagoService.borrar_pago`, que usa la compensación del ejemplo.
- Configurar los certificados de **mkcert** para probar HTTPS en local (ver [servicios](https://github.com/maxi627/servicios)).
- Revisar que los servicios no queden instanciados globalmente entre peticiones.
