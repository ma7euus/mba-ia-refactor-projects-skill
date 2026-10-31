COUNT_QUERIES = {
    "SELECT COUNT(*) AS TOTAL FROM PRODUTOS": "SELECT COUNT(*) AS total FROM produtos",
    "SELECT COUNT(*) AS TOTAL FROM USUARIOS": "SELECT COUNT(*) AS total FROM usuarios",
    "SELECT COUNT(*) AS TOTAL FROM PEDIDOS": "SELECT COUNT(*) AS total FROM pedidos",
    "SELECT COUNT(*) AS TOTAL FROM ITENS_PEDIDO": "SELECT COUNT(*) AS total FROM itens_pedido",
}


class SystemModel:
    def __init__(self, db):
        self.db = db

    def health(self):
        counts = dict(self.db.execute(
            "SELECT (SELECT COUNT(*) FROM produtos) AS produtos, "
            "(SELECT COUNT(*) FROM usuarios) AS usuarios, "
            "(SELECT COUNT(*) FROM pedidos) AS pedidos"
        ).fetchone())
        return {"status": "ok", "database": "connected", "counts": counts, "versao": "1.0.0"}

    def predefined_count(self, operation):
        return [dict(row) for row in self.db.execute(COUNT_QUERIES[operation])]

    def clear_data(self):
        self.db.execute("DELETE FROM itens_pedido")
        self.db.execute("DELETE FROM pedidos")
        self.db.execute("DELETE FROM produtos")
        self.db.execute("DELETE FROM usuarios")
