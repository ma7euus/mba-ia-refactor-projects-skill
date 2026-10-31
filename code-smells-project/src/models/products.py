from ..database import transaction
from ..errors import ApiError

PRODUCT_COLUMNS = "id, nome, descricao, preco, estoque, categoria, ativo, criado_em"


class ProductModel:
    def __init__(self, db):
        self.db = db

    def all(self):
        return [dict(row) for row in self.db.execute(
            f"SELECT {PRODUCT_COLUMNS} FROM produtos ORDER BY id"
        )]

    def find(self, product_id):
        row = self.db.execute(
            f"SELECT {PRODUCT_COLUMNS} FROM produtos WHERE id = ?", (product_id,)
        ).fetchone()
        return dict(row) if row else None

    def search(self, term, category=None, minimum=None, maximum=None):
        conditions, parameters = [], []
        if term:
            conditions.append("(nome LIKE ? OR descricao LIKE ?)")
            parameters.extend((f"%{term}%", f"%{term}%"))
        if category:
            conditions.append("categoria = ?")
            parameters.append(category)
        if minimum is not None:
            conditions.append("preco >= ?")
            parameters.append(minimum)
        if maximum is not None:
            conditions.append("preco <= ?")
            parameters.append(maximum)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        return [dict(row) for row in self.db.execute(
            f"SELECT {PRODUCT_COLUMNS} FROM produtos{where} ORDER BY id", parameters
        )]

    def create(self, data):
        with transaction(self.db):
            cursor = self.db.execute(
                "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) "
                "VALUES (?, ?, ?, ?, ?)",
                tuple(data[field] for field in ("nome", "descricao", "preco", "estoque", "categoria")),
            )
            return cursor.lastrowid

    def update(self, product_id, data):
        with transaction(self.db):
            cursor = self.db.execute(
                "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, "
                "categoria = ? WHERE id = ?",
                (*tuple(data[field] for field in ("nome", "descricao", "preco", "estoque", "categoria")), product_id),
            )
            if cursor.rowcount != 1:
                raise ApiError("Produto não encontrado", status=404)

    def delete(self, product_id):
        with transaction(self.db):
            if self.db.execute(
                "SELECT 1 FROM itens_pedido WHERE produto_id = ? LIMIT 1", (product_id,)
            ).fetchone():
                raise ApiError("Produto possui itens de pedido e não pode ser excluído", status=409)
            cursor = self.db.execute("DELETE FROM produtos WHERE id = ?", (product_id,))
            if cursor.rowcount != 1:
                raise ApiError("Produto não encontrado", status=404)
