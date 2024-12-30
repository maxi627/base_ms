import requests
from flask import current_app


class PagoService:

    def agregar_pago(self, data):
        try:
            # Enviar datos al servicio externo de pagos
            data_pago = data.get('pago')
              #TODO: verificar el estatus code que devuelve para ver si se compensa o no.
            response = requests.post(current_app.config['PAGOS_URL'], json=data_pago,verify=False)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Error adding pago: {e}")

    def borrar_pago(self, id_pago):
        try:
            # Eliminar un pago mediante su ID
            response = requests.delete(f"{current_app.config['PAGOS_URL']}/{id_pago}")
            if response.status_code == 404:
                return False
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            raise Exception(f"Error deleting pago with id {id_pago}: {e}")
