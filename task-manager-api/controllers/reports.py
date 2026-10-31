from errors import AppError
from models.task_repository import TaskRepository
from services.reporting import summary_report, user_statistics
from services.task_rules import positive_id
from utils.helpers import utc_now


class ReportController:
    def __init__(self, session):
        self.tasks = TaskRepository(session)

    def summary(self, actor):
        if actor.role != 'admin':
            raise AppError('Acesso negado', 403)
        now = utc_now()
        return summary_report(
            self.tasks.aggregate(now=now), self.tasks.overview_counts(),
            self.tasks.overdue_tasks(now), self.tasks.productivity(), now,
        )

    def user_report(self, actor, user_id):
        positive_id(user_id, 'user_id', nullable=False)
        if actor.role != 'admin' and actor.id != user_id:
            raise AppError('Acesso negado', 403)
        user = self.tasks.find_user(user_id)
        if user is None:
            raise AppError('Usuário não encontrado', 404)
        return user_statistics(user, self.tasks.aggregate(user_id=user_id))
