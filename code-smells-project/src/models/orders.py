class OrderModel:
    def __init__(self, db):
        self.db = db

    def user_exists(self, user_id):
        return self.db.execute("SELECT 1 FROM usuarios WHERE id = ?", (user_id,)).fetchone() is not None

    def products(self, product_ids):
        placeholders = ",".join("?" for _ in product_ids)
        return {row["id"]: dict(row) for row in self.db.execute(
            f"SELECT id, nome, preco, estoque FROM produtos WHERE id IN ({placeholders})", product_ids
        )}

    def insert(self, user_id, total):
        return self.db.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)",
            (user_id, total),
        ).lastrowid

    def reserve(self, product_id, quantity):
        return self.db.execute(
            "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
            (quantity, product_id, quantity),
        ).rowcount == 1

    def insert_item(self, order_id, product_id, quantity, price):
        self.db.execute(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) "
            "VALUES (?, ?, ?, ?)", (order_id, product_id, quantity, price),
        )

    def set_status(self, order_id, status):
        return self.db.execute(
            "UPDATE pedidos SET status = ? WHERE id = ?", (status, order_id)
        ).rowcount == 1

    def list(self, usuario_id=None):
        where = " WHERE p.usuario_id = ?" if usuario_id is not None else ""
        parameters = (usuario_id,) if usuario_id is not None else ()
        rows = self.db.execute(
            "SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em, "
            "i.id AS item_id, i.produto_id, i.quantidade, i.preco_unitario, "
            "COALESCE(pr.nome, 'Desconhecido') AS produto_nome "
            "FROM pedidos p LEFT JOIN itens_pedido i ON i.pedido_id = p.id "
            "LEFT JOIN produtos pr ON pr.id = i.produto_id" + where + " ORDER BY p.id, i.id",
            parameters,
        )
        orders = {}
        for row in rows:
            order = orders.setdefault(row["id"], {
                "id": row["id"], "usuario_id": row["usuario_id"], "status": row["status"],
                "total": row["total"], "criado_em": row["criado_em"], "itens": [],
            })
            if row["item_id"] is not None:
                order["itens"].append({
                    "produto_id": row["produto_id"], "produto_nome": row["produto_nome"],
                    "quantidade": row["quantidade"], "preco_unitario": row["preco_unitario"],
                })
        return list(orders.values())
