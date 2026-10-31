from werkzeug.security import generate_password_hash

from ..database import transaction
from ..errors import ApiError

USER_COLUMNS = "id, nome, email, senha, tipo, criado_em, ativo"


class UserModel:
    def __init__(self, db):
        self.db = db

    def all(self):
        return [dict(row) for row in self.db.execute(
            f"SELECT {USER_COLUMNS} FROM usuarios ORDER BY id"
        )]

    def find(self, user_id):
        row = self.db.execute(
            f"SELECT {USER_COLUMNS} FROM usuarios WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None

    def find_by_email(self, email):
        row = self.db.execute(
            f"SELECT {USER_COLUMNS} FROM usuarios WHERE email = ?", (email,)
        ).fetchone()
        return dict(row) if row else None

    def create(self, data, role="cliente"):
        if role not in {"cliente", "admin"}:
            raise ApiError("Tipo de usuário inválido")
        password_hash = generate_password_hash(data["senha"])
        with transaction(self.db):
            if self.find_by_email(data["email"]):
                raise ApiError("Email já cadastrado", status=409)
            cursor = self.db.execute(
                "INSERT INTO usuarios (nome, email, senha, tipo, ativo) VALUES (?, ?, ?, ?, 1)",
                (data["nome"], data["email"], password_hash, role),
            )
            return cursor.lastrowid
