from ..errors import ApiError
from ..validation import integer


def require_owner(identity, user_id):
    if identity["tipo"] != "admin" and identity["id"] != user_id:
        raise ApiError("Acesso não permitido", 403)


class OrderController:
    def __init__(self, service):
        self.service = service

    def create(self, data, identity):
        user_id = integer(data.get("usuario_id"), "Usuario ID", minimum=1)
        require_owner(identity, user_id)
        return self.service.create(data)

    def list(self, user_id=None):
        return self.service.list(user_id)

    def update_status(self, order_id, data):
        self.service.update_status(order_id, data)
