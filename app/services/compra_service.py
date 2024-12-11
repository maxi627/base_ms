import requests
from flask import current_app

class CompraService:

    def comprar(self, data):
        try:
            data_compra = data.get('compra')
            response = requests.post(current_app.config['COMPRAS_URL'], json=data_compra)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Error performing compra: {e}")

    def borrar_compra(self, id_compra):
        try:
            response = requests.delete(f"{current_app.config['COMPRAS_URL']}/{id_compra}")
            if response.status_code == 404:
                return False
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            raise Exception(f"Error deleting compra with id {id_compra}: {e}")
