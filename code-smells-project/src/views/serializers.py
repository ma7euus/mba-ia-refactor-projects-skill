"""Public representations selected explicitly; credentials never leave the API."""
PRODUCT_FIELDS = ("id", "nome", "descricao", "preco", "estoque", "categoria", "ativo", "criado_em")
USER_FIELDS = ("id", "nome", "email", "tipo", "criado_em")
LOGIN_FIELDS = ("id", "nome", "email", "tipo")
ORDER_FIELDS = ("id", "usuario_id", "status", "total", "criado_em")
ITEM_FIELDS = ("produto_id", "produto_nome", "quantidade", "preco_unitario")


def select(record, fields):
    return {key: record[key] for key in fields}


def product(record):
    return select(record, PRODUCT_FIELDS)


def user(record):
    return select(record, USER_FIELDS)


def login_user(record):
    return select(record, LOGIN_FIELDS)


def order(record):
    return {**select(record, ORDER_FIELDS), "itens": [select(item, ITEM_FIELDS) for item in record["itens"]]}
