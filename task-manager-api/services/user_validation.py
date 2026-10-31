"""Shared create/update/login policy, independent from HTTP."""

import re

from errors import AppError
from services.text_validation import utf8_text


MIN_PASSWORD_LENGTH = 4
MAX_PASSWORD_LENGTH = 1024
VALID_ROLES = frozenset(('user', 'manager', 'admin'))


def object_data(data):
    if not isinstance(data, dict) or not data:
        raise AppError('Dados inválidos', 400)
    return data


def validate_name(value):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 100:
        raise AppError('Nome deve ter entre 1 e 100 caracteres', 400)
    return utf8_text(value.strip())


def validate_email(value):
    if (not isinstance(value, str) or len(value) > 150
            or not re.fullmatch(r'[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+', value)):
        raise AppError('Email inválido', 400)
    return utf8_text(value)


def validate_password(value):
    if not isinstance(value, str) or not MIN_PASSWORD_LENGTH <= len(value) <= MAX_PASSWORD_LENGTH:
        raise AppError('Senha deve ter entre 4 e 1024 caracteres', 400)
    return utf8_text(value)


def user_fields(data, creating=False):
    data = object_data(data)
    result = {}
    if creating:
        for field, message in (('name', 'Nome é obrigatório'),
                               ('email', 'Email é obrigatório'),
                               ('password', 'Senha é obrigatória')):
            if field not in data or data[field] is None or data[field] == '':
                raise AppError(message, 400)
    validators = {'name': validate_name, 'email': validate_email, 'password': validate_password}
    for field, validate in validators.items():
        if field in data:
            result[field] = validate(data[field])
    if 'role' in data:
        if not isinstance(data['role'], str) or data['role'] not in VALID_ROLES:
            raise AppError('Role inválido', 400)
        result['role'] = data['role']
    if 'active' in data:
        if not isinstance(data['active'], bool):
            raise AppError('Active deve ser booleano', 400)
        result['active'] = data['active']
    return result


def login_fields(data):
    """Authenticate existing credentials without imposing new signup policy.

    Legacy SQLite rows may contain emails/passwords longer than the current
    creation limits. The HTTP body limit bounds resource use; authentication
    must still allow those accounts to verify and migrate their password hash.
    """
    data = object_data(data)
    email = data.get('email')
    password = data.get('password')
    if (not isinstance(email, str) or not email
            or not isinstance(password, str) or not password):
        raise AppError('Email e senha são obrigatórios', 400)
    return utf8_text(email), utf8_text(password)
