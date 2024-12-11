import requests
from flask import current_app

class StockService:

    def agregar_stock(self, data):
        try:
            # Enviar datos al servicio externo de Stock
            data_stock = data.get('stock')
            response = requests.post(current_app.config['STOCK_URL'], json=data_stock)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Error adding stock: {e}")

    def borrar_stock(self, id_stock):
        try:
            # Eliminar un stock mediante su ID
            response = requests.delete(f"{current_app.config['STOCK_URL']}/{id_stock}")
            if response.status_code == 404:
                return False
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            raise Exception(f"Error deleting stock with id {id_stock}: {e}")
