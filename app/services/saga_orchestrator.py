#TODO: ver el limiter y agregarlo al principio (probar  con 50 peticiones por segundo)
import logging

logger = logging.getLogger(__name__)


class Action:
    """Define un paso de la Saga: una función que ejecuta y otra que compensa."""
    def __init__(self, execute_fn, compensate_fn):
        self.execute_fn = execute_fn
        self.compensate_fn = compensate_fn

    def execute(self, data):
        """Ejecuta el paso llamando al microservicio. Devuelve (url, respuesta JSON)."""
        return self.execute_fn(data)

    def compensate(self, id):
        """Compensa el paso eliminando el recurso creado."""
        return self.compensate_fn(id)


class Saga:
    """Orquestador de la saga: ejecuta los pasos en orden y compensa si alguno falla."""
    def __init__(self, actions, data):
        self.actions = actions
        self.data = data
        self.IDs = []
        self.response = {"message": "OK", "status_code": 201, "data": {"message": "Operación realizada con éxito"}}

    def execute(self):
        """Ejecuta la saga en orden y maneja la compensación en caso de fallo."""
        for index, action in enumerate(self.actions):
            try:
                # La acción ya hace el POST al microservicio: no se vuelve a enviar.
                _, response_data = action.execute(self.data)
                id_generado = (response_data.get("data") or {}).get("id")
                logger.info(f"Paso {index} completado. ID generado: {id_generado}")
                self.IDs.append(id_generado)
            except Exception as e:
                logger.error(f"Falló el paso {index}: {e}")
                self.response = {
                    "message": "Error durante la ejecución de la saga",
                    "status_code": 500,
                    "data": {"error": str(e), "paso": index},
                }
                self.compensate()
                break

        logger.info(f"Estado final de IDs: {self.IDs}")
        return self.response

    def compensate(self):
        """Compensa en orden inverso todos los pasos que se completaron."""
        for i in range(len(self.IDs) - 1, -1, -1):
            id_recurso = self.IDs[i]
            if id_recurso is None:
                logger.warning(f"No hay ID disponible para compensar el paso {i}")
                continue
            try:
                self.actions[i].compensate(id_recurso)
                logger.info(f"Paso {i} compensado (ID {id_recurso})")
            except Exception as e:
                # Se sigue compensando el resto aunque uno falle.
                logger.exception(f"Error al compensar el paso {i} (ID {id_recurso}): {e}")
