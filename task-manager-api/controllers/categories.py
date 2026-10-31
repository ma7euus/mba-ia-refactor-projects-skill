from errors import AppError
from models.category_repository import CategoryRepository
from services.task_rules import category_values, positive_id


class CategoryController:
    def __init__(self, session):
        self.session = session
        self.categories = CategoryRepository(session)

    @staticmethod
    def _require_admin(actor):
        if actor.role != 'admin':
            raise AppError('Acesso negado', 403)

    def _find(self, category_id):
        positive_id(category_id, 'category_id', nullable=False)
        category = self.categories.find(category_id)
        if category is None:
            raise AppError('Categoria não encontrada', 404)
        return category

    def list_categories(self, actor):
        return self.categories.list_with_counts()

    def create_category(self, actor, data):
        self._require_admin(actor)
        category = self.categories.add(category_values(data, creating=True))
        self.session.commit()
        return category

    def update_category(self, actor, category_id, data):
        self._require_admin(actor)
        category = self._find(category_id)
        values = category_values(data)
        for field, value in values.items():
            setattr(category, field, value)
        self.session.commit()
        return category

    def delete_category(self, actor, category_id):
        self._require_admin(actor)
        category = self._find(category_id)
        self.categories.delete_preserving_tasks(category)
        self.session.commit()
        return {'message': 'Categoria deletada'}
