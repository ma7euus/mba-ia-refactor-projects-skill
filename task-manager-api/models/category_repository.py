from sqlalchemy import func, select, update

from models.category import Category
from models.task import Task


class CategoryRepository:
    def __init__(self, session):
        self.session = session

    def find(self, category_id):
        return self.session.get(Category, category_id)

    def list_with_counts(self):
        return self.session.execute(select(Category, func.count(Task.id)).outerjoin(
            Task, Task.category_id == Category.id
        ).group_by(Category.id).order_by(Category.id)).all()

    def add(self, values):
        category = Category(**values)
        self.session.add(category)
        return category

    def delete_preserving_tasks(self, category):
        self.session.execute(update(Task).where(Task.category_id == category.id).values(category_id=None))
        self.session.delete(category)
