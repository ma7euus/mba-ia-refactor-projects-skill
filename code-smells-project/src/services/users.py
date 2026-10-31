import logging

from werkzeug.security import check_password_hash

from ..errors import ApiError
from ..validation import object_data, text

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, model):
        self.model = model

    def create(self, data):
        data = object_data(data)
        if not all(data.get(field) for field in ("nome", "email", "senha")):
            raise ApiError("Nome, email e senha são obrigatórios")
        if data.get("tipo", "cliente") != "cliente":
            raise ApiError("Cadastro público permite apenas clientes")
        email = text(data["email"], "Email", maximum=254)
        if "@" not in email or any(character.isspace() for character in email):
            raise ApiError("Email inválido")
        validated = {
            "nome": text(data["nome"], "Nome", minimum=2),
            "email": email,
            "senha": text(data["senha"], "Senha", maximum=1024),
        }
        user_id = self.model.create(validated)
        logger.info("Usuário criado id=%s", user_id)
        return user_id

    def authenticate(self, email, password):
        if not isinstance(email, str) or not isinstance(password, str) or not email or not password:
            return None
        user = self.model.find_by_email(email)
        if user is None or not user["ativo"]:
            return None
        if not check_password_hash(user["senha"], password):
            return None
        return user
