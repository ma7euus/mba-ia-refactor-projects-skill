class ReportModel:
    def __init__(self, db):
        self.db = db

    def sales_summary(self):
        row = self.db.execute(
            "SELECT COUNT(*) AS total_pedidos, COALESCE(SUM(total), 0) AS faturamento, "
            "COALESCE(SUM(CASE WHEN status = 'pendente' THEN 1 ELSE 0 END), 0) AS pendentes, "
            "COALESCE(SUM(CASE WHEN status = 'aprovado' THEN 1 ELSE 0 END), 0) AS aprovados, "
            "COALESCE(SUM(CASE WHEN status = 'cancelado' THEN 1 ELSE 0 END), 0) AS cancelados "
            "FROM pedidos"
        ).fetchone()
        return dict(row)
