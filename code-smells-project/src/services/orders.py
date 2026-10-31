import logging
import math

from ..database import transaction
from ..errors import ApiError
from ..models.orders import OrderModel
from ..validation import ORDER_STATUSES, SQLITE_MAX_INTEGER, integer, object_data

logger = logging.getLogger(__name__)


class OrderService:
    def __init__(self, db):
        self.db = db
        self.model = OrderModel(db)

    def create(self, data):
        data = object_data(data)
        user_id = integer(data.get("usuario_id"), "Usuario ID", minimum=1)
        items = data.get("itens")
        if not isinstance(items, list) or not items:
            raise ApiError("Pedido deve ter pelo menos 1 item")
        if len(items) > 1000:
            raise ApiError("Pedido excede o limite de itens")
        quantities = {}
        for item in items:
            item = object_data(item)
            product_id = integer(item.get("produto_id"), "Produto ID", minimum=1)
            quantity = integer(item.get("quantidade"), "Quantidade", minimum=1)
            aggregated = quantities.get(product_id, 0) + quantity
            if aggregated > SQLITE_MAX_INTEGER:
                raise ApiError("Quantidade fora da faixa permitida")
            quantities[product_id] = aggregated

        with transaction(self.db):
            if not self.model.user_exists(user_id):
                raise ApiError("Usuário não encontrado", status=404)
            products = self.model.products(tuple(quantities))
            total = 0.0
            for product_id, quantity in quantities.items():
                product = products.get(product_id)
                if product is None:
                    raise ApiError(f"Produto {product_id} não encontrado")
                if product["estoque"] < quantity:
                    raise ApiError("Estoque insuficiente para " + product["nome"])
                try:
                    line_total = product["preco"] * quantity
                    total += line_total
                except (TypeError, OverflowError):
                    raise ApiError("Preço do produto inválido", status=409) from None
                if not math.isfinite(total) or total < 0:
                    raise ApiError("Total do pedido fora da faixa permitida")
            total = round(total, 2)
            order_id = self.model.insert(user_id, total)
            for product_id, quantity in quantities.items():
                if not self.model.reserve(product_id, quantity):
                    raise ApiError("Estoque insuficiente para " + products[product_id]["nome"])
                self.model.insert_item(order_id, product_id, quantity, products[product_id]["preco"])

        logger.info("Notificações simuladas de email, SMS e push: pedido criado id=%s", order_id)
        return {"pedido_id": order_id, "total": total}

    def list(self, usuario_id=None):
        return self.model.list(usuario_id)

    def update_status(self, order_id, data):
        data = object_data(data)
        status = data.get("status")
        if not isinstance(status, str) or status not in ORDER_STATUSES:
            raise ApiError("Status inválido")
        with transaction(self.db):
            if not self.model.set_status(order_id, status):
                raise ApiError("Pedido não encontrado", status=404)
        logger.info("Notificação simulada: status do pedido id=%s atualizado para %s", order_id, status)
