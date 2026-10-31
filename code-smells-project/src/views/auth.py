from functools import wraps
from flask import g, request
from ..controllers.orders import require_owner
from ..errors import ApiError


def protected(admin=False):
    def decorate(handler):
        @wraps(handler)
        def authenticate(*args, **kwargs):
            credentials = request.authorization
            if credentials is None or credentials.type.lower() != "basic":
                raise ApiError("Autenticação obrigatória", 401)
            user = g.controllers["users"].authenticate(credentials.username, credentials.password)
            if user is None:
                raise ApiError("Credenciais inválidas", 401)
            if admin and user["tipo"] != "admin":
                raise ApiError("Acesso não permitido", 403)
            g.identity = user
            return handler(*args, **kwargs)
        return authenticate
    return decorate


def owner(user_id):
    require_owner(g.identity, user_id)
