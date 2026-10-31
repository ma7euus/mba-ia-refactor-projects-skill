from errors import AppError
from models.task_repository import TaskRepository
from services.task_rules import positive_id, search_filters, task_values
from services.reporting import task_statistics
from utils.helpers import utc_now


class TaskController:
    def __init__(self, session):
        self.session = session
        self.tasks = TaskRepository(session)

    def _find_allowed(self, actor, task_id):
        positive_id(task_id, 'task_id', nullable=False)
        task = self.tasks.find(task_id)
        if task is None:
            raise AppError('Task não encontrada', 404)
        if actor.role != 'admin' and task.user_id != actor.id:
            raise AppError('Acesso negado', 403)
        return task

    def _check_relations(self, values):
        if values.get('user_id') is not None and self.tasks.find_user(values['user_id']) is None:
            raise AppError('Usuário não encontrado', 404)
        if values.get('category_id') is not None and self.tasks.find_category(values['category_id']) is None:
            raise AppError('Categoria não encontrada', 404)

    def list_tasks(self, actor):
        return self.tasks.list(user_id=None if actor.role == 'admin' else actor.id, with_names=True)

    def get_task(self, actor, task_id):
        return self._find_allowed(actor, task_id)

    def create_task(self, actor, data):
        values = task_values(data, creating=True)
        if actor.role != 'admin':
            if 'user_id' not in data:
                values['user_id'] = actor.id
            if values['user_id'] != actor.id:
                raise AppError('Acesso negado', 403)
        self._check_relations(values)
        task = self.tasks.add(values)
        self.session.commit()
        return task

    def update_task(self, actor, task_id, data):
        task = self._find_allowed(actor, task_id)
        values = task_values(data)
        if actor.role != 'admin' and 'user_id' in values and values['user_id'] != actor.id:
            raise AppError('Acesso negado', 403)
        self._check_relations(values)
        for field, value in values.items():
            setattr(task, field, value)
        task.updated_at = utc_now()
        self.session.commit()
        return task

    def delete_task(self, actor, task_id):
        task = self._find_allowed(actor, task_id)
        self.tasks.delete(task)
        self.session.commit()
        return {'message': 'Task deletada com sucesso'}

    def search_tasks(self, actor, filters):
        filters = search_filters(filters)
        if actor.role != 'admin' and filters.get('user_id', actor.id) != actor.id:
            raise AppError('Acesso negado', 403)
        return self.tasks.list(user_id=None if actor.role == 'admin' else actor.id, filters=filters)

    def stats(self, actor):
        aggregate = self.tasks.aggregate(user_id=None if actor.role == 'admin' else actor.id)
        return task_statistics(aggregate)
