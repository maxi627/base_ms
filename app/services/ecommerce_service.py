import requests
from tenacity import retry, stop_after_attempt, wait_random
from flask import current_app


class StockService:
  #TODO: verificar el estatus code que devuelve para ver si se compensa o no.

    @retry(wait=wait_random(min=1, max=2), stop=stop_after_attempt(3))
    def obtener_producto(self, id_producto):
        try:
            #TODO: obtener por cache el stock de ese producto, si es mayor que cero, sino compensar
            response = requests.get(f"{current_app.config['STOCK_URL']}/{id_producto}",verify=False)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return schema.load(response.json())
        except requests.RequestException as e:
            raise Exception(f"Error fetching producto with id {id_producto}: {e}")
