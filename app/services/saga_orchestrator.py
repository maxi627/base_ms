from typing import List
from app.services import CompraService, PagoService, StockService


#TODO: Servicios instanciados globalmente, que pasa sí un hilo se utiliza antes de cerrarse la petición

compra_service = CompraService()
pago_service = PagoService()
stock_service = StockService()

#TODO: ver el limiter y agregarlo al principio (probar  con 50 peticiones por segundo)
class Action:
    def __init__(self, action, compensation):
        self.action = action
        self.compensation = compensation

    def execute(self, data):
        request = self.action(data)
        return request

    def compensate(self, data):
        self.compensation(data)

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
                response = action.execute(self.data)
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

    def compensate(self, index):
        for i in range(index - 1, -1, -1):
            self.actions[i].compensate(self.IDs[i])

class SagaBuilder:
    def __init__(self):
        self.actions = []
        self.data = None  

    def action(self, action, compensation):
        self.actions.append(Action(action, compensation))
        return self

    def set_data(self, data):
        self.data = data
        return self

    def build(self):
        return Saga(self.actions, self.data)

