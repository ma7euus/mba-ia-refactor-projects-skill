"""User persistence and aggregate reads with an injected session."""

from sqlalchemy import delete, func, select

from models.auth_session import AuthSession
from models.task import Task
from models.user import User


class UserRepository:
    def __init__(self, session):
        self.session = session

    def get(self, user_id):
        return self.session.get(User, user_id)

    def by_email(self, email):
        return self.session.scalar(select(User).where(User.email == email))

    def with_task_counts(self):
        return self.session.execute(
            select(User, func.count(Task.id))
            .outerjoin(Task, Task.user_id == User.id)
            .group_by(User.id)
            .order_by(User.id)
        ).all()

    def tasks(self, user_id):
        return self.session.scalars(
            select(Task).where(Task.user_id == user_id).order_by(Task.id)
        ).all()

    def add(self, user):
        self.session.add(user)

    def revoke_sessions(self, user_id):
        self.session.execute(delete(AuthSession).where(AuthSession.user_id == user_id))

    def delete(self, user):
        self.revoke_sessions(user.id)
        self.session.execute(delete(Task).where(Task.user_id == user.id))
        self.session.delete(user)
