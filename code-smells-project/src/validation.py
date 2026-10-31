"""Input and domain primitives, independent of the HTTP transport."""

import math

from .errors import ApiError

SQLITE_MAX_INTEGER = 2**63 - 1
PRODUCT_CATEGORIES = frozenset({
    "informatica", "moveis", "vestuario", "geral", "eletronicos", "livros",
})
ORDER_STATUSES = frozenset({"pendente", "aprovado", "enviado", "entregue", "cancelado"})


def object_data(value):
    if not isinstance(value, dict):
        raise ApiError("Dados inválidos")
    return value


def text(value, field, minimum=1, maximum=200):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ApiError(f"{field} inválido")
    return value


def integer(value, field, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ApiError(f"{field} deve ser inteiro")
    if not minimum <= value <= SQLITE_MAX_INTEGER:
        raise ApiError(f"{field} fora da faixa permitida")
    return value


def nonnegative_number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ApiError(f"{field} deve ser numérico")
    try:
        converted = float(value)
    except (ValueError, OverflowError):
        raise ApiError(f"{field} inválido") from None
    if not math.isfinite(converted) or converted < 0:
        raise ApiError(f"{field} deve ser finito e não negativo")
    return converted


def query_price(value, field):
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ApiError(f"{field} inválido")
    try:
        parsed = float(value)
    except ValueError:
        raise ApiError(f"{field} inválido") from None
    return nonnegative_number(parsed, field)


def product_data(value):
    value = object_data(value)
    for field, label in (("nome", "Nome"), ("preco", "Preço"), ("estoque", "Estoque")):
        if field not in value:
            raise ApiError(f"{label} é obrigatório")
    name = text(value["nome"], "Nome", minimum=2)
    description = value.get("descricao", "")
    if not isinstance(description, str) or len(description) > 10000:
        raise ApiError("Descrição inválida")
    category = value.get("categoria", "geral")
    if not isinstance(category, str) or category not in PRODUCT_CATEGORIES:
        raise ApiError("Categoria inválida")
    return {
        "nome": name,
        "descricao": description,
        "preco": nonnegative_number(value["preco"], "Preço"),
        "estoque": integer(value["estoque"], "Estoque"),
        "categoria": category,
    }
