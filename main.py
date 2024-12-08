import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from app.config import factory

# Cargar configuración según el entorno
env = os.getenv("FLASK_ENV", "development")
config = factory(env)

# Crear la aplicación
app = Flask(__name__)
app.config.from_object(config)

# Inicializar la base de datos
db = SQLAlchemy(app)

if __name__ == "__main__":
    # Inicia la app para pruebas locales (opcional)
    app.run(host="0.0.0.0", port=5001)
