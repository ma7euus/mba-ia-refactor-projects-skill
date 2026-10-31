import math

from ..errors import ApiError
from ..models.reports import ReportModel

# Descending thresholds preserve the legacy strict `>` comparisons.
DISCOUNT_TIERS = ((10000, 0.10), (5000, 0.05), (1000, 0.02))


def applicable_discount(revenue):
    for threshold, rate in DISCOUNT_TIERS:
        if revenue > threshold:
            return revenue * rate
    return 0


class ReportService:
    def __init__(self, db):
        self.model = ReportModel(db)

    def sales(self):
        summary = self.model.sales_summary()
        count = summary["total_pedidos"]
        revenue = summary["faturamento"]
        if not math.isfinite(revenue):
            raise ApiError("Faturamento fora da faixa numérica permitida", status=409)
        discount = applicable_discount(revenue)
        return {
            "total_pedidos": count,
            "faturamento_bruto": round(revenue, 2),
            "desconto_aplicavel": round(discount, 2),
            "faturamento_liquido": round(revenue - discount, 2),
            "pedidos_pendentes": summary["pendentes"],
            "pedidos_aprovados": summary["aprovados"],
            "pedidos_cancelados": summary["cancelados"],
            "ticket_medio": round(revenue / count, 2) if count else 0,
        }
