from dataclasses import dataclass

@dataclass
class ResponseMessage:
  
    message: str = None
    status_code: int = None
    data: dict = None

@dataclass
class ResponseBuilder:
    message: str = None
    status_code: int = None
    data: dict = None

    def add_message(self, message: str):
        self.message = message
        return self
    
    def add_status_code(self, status_code: int):
        self.status_code = status_code
        return self
    
    def add_data(self, data: dict):
        self.data = data
        return self
    
    def build(self):
        return ResponseMessage(
            message=self.message,
            status_code=self.status_code,
            data=self.data
        )