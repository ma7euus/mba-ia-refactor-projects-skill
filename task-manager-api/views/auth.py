"""HTTP adaptation of the injected authentication service."""

from functools import wraps

from flask import g, request

from errors import AppError


def require_auth(auth_service, admin=False):
    def decorate(handler):
        @wraps(handler)
        def authenticated(*args, **kwargs):
            parts = request.headers.get('Authorization', '').split()
            if len(parts) != 2 or parts[0].lower() != 'bearer':
                raise AppError('Autenticação necessária', 401)
            g.user = auth_service.authenticate(parts[1])
            if admin and g.user.role != 'admin':
                raise AppError('Acesso não permitido', 403)
            return handler(*args, **kwargs)
        return authenticated
    return decorate
