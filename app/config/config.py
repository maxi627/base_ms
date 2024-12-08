import os

from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, "..", ".env"))  # Ajusta la ruta según tu estructura

class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    @staticmethod
    def init_app(app):
        """Método para inicializar configuraciones adicionales si es necesario."""
        pass

    @staticmethod
    def validate_required_env_vars(env_vars):
        """Valida que las variables de entorno críticas estén definidas."""
        missing_vars = [var for var in env_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Las siguientes variables de entorno faltan o están vacías: {', '.join(missing_vars)}")

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv('DEV_DATABASE_URI')

    @staticmethod
    def init_app(app):
        Config.validate_required_env_vars(['DEV_DATABASE_URI'])

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv('TEST_DB_URI')

    @staticmethod
    def init_app(app):
        Config.validate_required_env_vars(['TEST_DB_URI'])

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('PROD_DATABASE_URI')

    @staticmethod
    def init_app(app):
        Config.validate_required_env_vars(['PROD_DATABASE_URI'])

def factory(env="development"):
    """Devuelve la configuración adecuada según el entorno."""
    configs = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }
    return configs.get(env, DevelopmentConfig)
