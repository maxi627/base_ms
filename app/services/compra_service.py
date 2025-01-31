
#TODO: aplicar retry

            #TODO: verificar el estatus code que devuelve para ver si se compensa o no.
import requests
import logging
from flask import current_app
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,  # Cambia a DEBUG para mayor detalle
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)  # Nombre del logger, generalmente el nombre del módulo

class CompraService:
    """
    Servicio para interactuar con el microservicio de compras.
    """

    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_fixed(2)
    )
    def comprar(self, data):
        """
        Realiza una compra enviando una solicitud POST al servicio de compras.
        :param data: Diccionario con los datos de la compra.
        :return: Respuesta JSON del servicio de compras.
        :raises Exception: Si ocurre un error en la solicitud.
        """
        try:
            logger.info("Iniciando el proceso de compra con datos: %s", data)
            data_compra = data.get('compra')
            response = requests.post(
                current_app.config['COMPRAS_URL'],
                json=data_compra,
                verify=False  # Cambiar a True en producción
            )

            # Verificar el código de estado
            if response.status_code == 201:
                logger.info("Compra realizada con éxito: %s", response.json())
                return response.json()
            elif response.status_code == 409:
                logger.warning("Conflicto: la compra ya existe.")
                raise Exception("Compra ya existe (conflicto).")
            elif response.status_code == 422:
                logger.warning("Datos inválidos enviados: %s", response.json())
                raise Exception(f"Datos inválidos: {response.json().get('errors', 'No especificado')}")
            else:
                logger.error("Error inesperado: %s - %s", response.status_code, response.text)
                raise Exception(f"Error inesperado: {response.status_code} - {response.text}")

        except requests.RequestException as e:
            logger.exception("Error de red durante la compra.")
            raise Exception(f"Error al realizar la compra: {str(e)}")

    def borrar_compra(self, id_compra):
        """
        Envía una solicitud DELETE al servicio de compras para borrar una compra específica.
        :param id_compra: ID de la compra a borrar.
        :return: True si la compra fue eliminada, False si no se encontró.
        :raises Exception: Si ocurre un error en la solicitud.
        """
        try:
            logger.info("Iniciando la eliminación de la compra con ID: %s", id_compra)
            response = requests.delete(
                f"{current_app.config['COMPRAS_URL']}/{id_compra}",
                verify=False  # Cambiar a True en producción
            )

            if response.status_code == 404:
                logger.warning("Compra con ID %s no encontrada.", id_compra)
                return False
            elif response.status_code == 204:
                logger.info("Compra con ID %s eliminada con éxito.", id_compra)
                return True
            else:
                logger.error("Error inesperado al borrar la compra: %s - %s", response.status_code, response.text)
                raise Exception(f"Error inesperado al borrar la compra: {response.status_code} - {response.text}")

        except requests.RequestException as e:
            logger.exception("Error de red al borrar la compra con ID %s.", id_compra)
            raise Exception(f"Error al borrar la compra con ID {id_compra}: {str(e)}")
