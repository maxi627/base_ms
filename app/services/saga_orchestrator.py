


#TODO: ver el limiter y agregarlo al principio (probar  con 50 peticiones por segundo)
from typing import List
import requests
from limits import RateLimitItemPerSecond
from limits.decorators import limits

# Limitar a n peticiones por segundo
@limits(calls=5, period=1)
def hacer_peticion_limited(url, data):
    response = requests.post(url, json=data)
    return response

class Saga:
    def __init__(self, actions: List[Action], data):
        self.actions = actions
        self.data = data
        self.IDs = []

        # Response
        self.response = {
            "status_code": None,
            "message": None,
            "data": None
        }

    def execute(self):
        self.response['data'] = "Operación realizada con éxito"
        self.response['status_code'] = 201
        self.response['message'] = "OK"

        for index, action in enumerate(self.actions):
            try:
                # Utilizando el limitador
                response = hacer_peticion_limited(action.execute(self.data))
                if response.status_code == 201:
                    self.IDs.append(response.json().get('data').get('id'))
                else:
                    self.response['data'] = response.json().get('data')
                    self.response['status_code'] = response.status_code
                    self.response['message'] = response.json().get('message')
                    self.compensate(index)
                    break

            except Exception as e:
                self.response['data'] = str(e)
                self.response['status_code'] = 500
                self.response['message'] = "Error durante la ejecución de la saga"
                self.compensate(index)
                break

        return self.response
