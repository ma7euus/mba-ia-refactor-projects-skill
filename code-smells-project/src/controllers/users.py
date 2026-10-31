from ..errors import ApiError


class UserController:
    def __init__(self, model, service):
        self.model, self.service = model, service

    def list(self):
        return self.model.all()

    def find(self, user_id):
        user = self.model.find(user_id)
        if user is None:
            raise ApiError("Usuário não encontrado", 404)
        return user

    def create(self, data):
        return self.service.create(data)

    def authenticate(self, email, password):
        return self.service.authenticate(email, password)

    def login(self, data):
        email, password = data.get("email"), data.get("senha")
        if not isinstance(email, str) or not email or not isinstance(password, str) or not password:
            raise ApiError("Email e senha são obrigatórios")
        user = self.authenticate(email, password)
        if user is None:
            raise ApiError("Email ou senha inválidos", 401)
        return user
