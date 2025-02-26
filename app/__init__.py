import os
from flask import Flask
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from app.config import cache_config, factory
import redis
import logging
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import requests
import pybreaker

# Configuracion global de circuito breaker
circuit_breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=30)  # Configuración: 3 fallos antes de abrir

def obtener_circuit_breaker():
    return circuit_breaker
#configuracion global de retry
def retry_logic(func):
    """
    Aplica la lógica de retry a una función.
    """
    return retry(
        retry=retry_if_exception_type(requests.RequestException),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        reraise=True
    )(func)


# Configuración global de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Instancia global de extensiones
db = SQLAlchemy()
cache = Cache()

# Obtener las variables de entorno
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = int(os.getenv('REDIS_PORT', 6379))
redis_password = os.getenv('REDIS_PASSWORD', '')
redis_db = int(os.getenv('REDIS_DB', 0))

# Crear una instancia de Redis
redis_client = redis.StrictRedis(
    host=redis_host,
    port=redis_port,
    db=redis_db,
    password=redis_password,
    decode_responses=True
)



def create_app():
    app = Flask(__name__)
    app_context = os.getenv('FLASK_ENV', 'development')
    try:
        app.config.from_object(factory(app_context))
    except Exception as e:
        raise RuntimeError(f"Error al cargar la configuración para el entorno {app_context}: {e}")

    try:
        db.init_app(app)
        cache.init_app(app, config=cache_config) 
    except Exception as e:
        raise RuntimeError(f"Error al inicializar extensiones: {e}")


    # Ruta de prueba
    @app.route('/ping', methods=['GET'])
    def ping():
        return {"message": "El servicio de Base está en funcionamiento"}

    return app

