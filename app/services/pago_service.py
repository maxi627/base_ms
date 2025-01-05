
  #TODO: verificar el estatus code que devuelve para ver si se compensa o no.
    import requests
import logging
from flask import current_app
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Configuración del logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class PagoService:
    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        reraise=True
    )
    def agregar_pago(self, data):
        """
        Envía una solicitud POST al servicio de pagos para agregar un pago, con reintentos.
        :param data: Diccionario con los datos del pago.
        :return: Respuesta JSON del servicio de pagos.
        :raises Exception: Si ocurre un error en la solicitud.
        """
        try:
            data_pago = data.get('pago')
            logger.info("Enviando solicitud para agregar un pago: %s", data_pago)

            response = requests.post(
                current_app.config['PAGOS_URL'],
                json=data_pago,
                verify=False  # Cambiar a True y configurar certificados en producción.
            )

            logger.info("Respuesta del servicio de pagos: %s", response.status_code)

            if response.status_code == 201:
                logger.info("Pago creado exitosamente.")
                return response.json()
            elif response.status_code == 409:
                logger.warning("Pago ya existe (conflicto).")
                raise Exception("Pago ya existe (conflicto).")
            elif response.status_code == 422:
                error_details = response.json().get('errors', 'No especificado')
                logger.error("Datos inválidos: %s", error_details)
                raise Exception(f"Datos inválidos: {error_details}")
            else:
                logger.error("Error inesperado: %s - %s", response.status_code, response.text)
                raise Exception(f"Error inesperado: {response.status_code} - {response.text}")

        except requests.RequestException as e:
            logger.exception("Error al agregar el pago.")
            raise

    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        reraise=True
    )
    def borrar_pago(self, id_pago):
        """
        Envía una solicitud DELETE al servicio de pagos para eliminar un pago, con reintentos.
        :param id_pago: ID del pago a eliminar.
        :return: True si el pago fue eliminado, False si no se encontró.
        :raises Exception: Si ocurre un error en la solicitud.
        """
        try:
            logger.info("Enviando solicitud para eliminar el pago con ID: %s", id_pago)

            response = requests.delete(
                f"{current_app.config['PAGOS_URL']}/{id_pago}",
                verify=False  # Cambiar a True en producción.
            )

            logger.info("Respuesta del servicio al intentar eliminar el pago: %s", response.status_code)

            if response.status_code == 404:
                logger.warning("Pago con ID %s no encontrado.", id_pago)
                return False
            elif response.status_code == 204:
                logger.info("Pago con ID %s eliminado exitosamente.", id_pago)
                return True
            else:
                logger.error("Error inesperado al eliminar el pago: %s - %s", response.status_code, response.text)
                raise Exception(f"Error inesperado al eliminar el pago: {response.status_code} - {response.text}")

        except requests.RequestException as e:
            logger.exception("Error al eliminar el pago con ID %s.", id_pago)
            raise
