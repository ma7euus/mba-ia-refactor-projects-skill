"""Text encoding policy shared by inputs used in hashing and persistence."""

from errors import AppError


def utf8_text(value):
    """Validate an already type-checked string without changing its contents."""
    try:
        value.encode('utf-8')
    except UnicodeEncodeError:
        raise AppError('Texto contém caracteres Unicode inválidos', 400) from None
    return value
