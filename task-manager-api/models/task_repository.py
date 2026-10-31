"""Task queries and aggregate reads use a caller-owned SQLAlchemy session."""

from datetime import timedelta

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import joinedload

from models.category import Category
from models.task import Task
from models.user import User
from services.task_rules import FINISHED_STATUSES, VALID_STATUSES
from utils.helpers import utc_now


class TaskRepository:
    def __init__(self, session):
        self.session = session

    def find(self, task_id):
        return self.session.get(Task, task_id)

    def find_user(self, user_id):
        return self.session.get(User, user_id)

    def find_category(self, category_id):
        return self.session.get(Category, category_id)

    def list(self, user_id=None, filters=None, with_names=False):
        statement = select(Task).order_by(Task.id)
        if with_names:
            statement = statement.options(joinedload(Task.user), joinedload(Task.category))
        if user_id is not None:
            statement = statement.where(Task.user_id == user_id)
        filters = filters or {}
        if 'q' in filters:
            pattern = f"%{filters['q']}%"
            statement = statement.where(or_(Task.title.like(pattern), Task.description.like(pattern)))
        for field in ('status', 'priority', 'user_id'):
            if field in filters:
                statement = statement.where(getattr(Task, field) == filters[field])
        return self.session.scalars(statement).all()

    def add(self, values):
        task = Task(**values)
        self.session.add(task)
        return task

    def delete(self, task):
        self.session.delete(task)

    def aggregate(self, user_id=None, now=None):
        now = now or utc_now()
        columns = [func.count(Task.id).label('total')]
        predicates = {status: Task.status == status for status in VALID_STATUSES}
        predicates.update({
            'overdue': (Task.due_date < now) & Task.status.not_in(FINISHED_STATUSES),
            'high_priority': Task.priority <= 2,
            'recent_created': Task.created_at >= now - timedelta(days=7),
            'recent_done': (Task.status == 'done') & (Task.updated_at >= now - timedelta(days=7)),
        })
        predicates.update({f'priority_{priority}': Task.priority == priority for priority in range(1, 6)})
        columns.extend(func.coalesce(func.sum(case((condition, 1), else_=0)), 0).label(name)
                       for name, condition in predicates.items())
        statement = select(*columns)
        if user_id is not None:
            statement = statement.where(Task.user_id == user_id)
        return dict(self.session.execute(statement).mappings().one())

    def overdue_tasks(self, now):
        return self.session.scalars(select(Task).where(
            Task.due_date < now, Task.status.not_in(FINISHED_STATUSES)
        ).order_by(Task.id)).all()

    def overview_counts(self):
        return self.session.execute(select(
            select(func.count(User.id)).scalar_subquery().label('total_users'),
            select(func.count(Category.id)).scalar_subquery().label('total_categories'),
        )).mappings().one()

    def productivity(self):
        return self.session.execute(select(
            User.id.label('user_id'), User.name.label('user_name'),
            func.count(Task.id).label('total_tasks'),
            func.coalesce(func.sum(case((Task.status == 'done', 1), else_=0)), 0).label('completed_tasks'),
        ).outerjoin(Task, Task.user_id == User.id).group_by(User.id, User.name).order_by(User.id)).mappings().all()
