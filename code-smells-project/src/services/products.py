import logging

from ..errors import ApiError
from ..validation import PRODUCT_CATEGORIES, object_data, product_data, query_price

logger = logging.getLogger(__name__)


class ProductService:
    def __init__(self, model):
        self.model = model

    def all(self):
        return self.model.all()

    def find(self, product_id):
        product = self.model.find(product_id)
        if product is None:
            raise ApiError("Produto não encontrado", status=404)
        return product

    def search(self, query):
        term = query.get("q", "")
        category = query.get("categoria")
        if not isinstance(term, str) or len(term) > 1000:
            raise ApiError("Termo de busca inválido")
        if category and (not isinstance(category, str) or category not in PRODUCT_CATEGORIES):
            raise ApiError("Categoria inválida")
        minimum = query_price(query.get("preco_min"), "Preço mínimo")
        maximum = query_price(query.get("preco_max"), "Preço máximo")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ApiError("Preço mínimo maior que preço máximo")
        return self.model.search(term, category, minimum, maximum)

    def create(self, data):
        product_id = self.model.create(product_data(data))
        logger.info("Produto criado id=%s", product_id)
        return product_id

    def update(self, product_id, data):
        self.find(product_id)
        self.model.update(product_id, product_data(data))
        logger.info("Produto atualizado id=%s", product_id)

    def delete(self, product_id):
        self.model.delete(product_id)
        logger.info("Produto excluído id=%s", product_id)
