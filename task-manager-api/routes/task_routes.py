from flask import Blueprint, g, jsonify, request

from views.auth import require_auth
from views.tasks import serialize_task


def create_task_blueprint(controller, auth_service):
    blueprint = Blueprint('tasks', __name__)

    @blueprint.get('/tasks')
    @require_auth(auth_service)
    def get_tasks():
        return jsonify([serialize_task(task, overdue=True, names=True)
                        for task in controller.list_tasks(g.user)]), 200

    @blueprint.get('/tasks/<int:task_id>')
    @require_auth(auth_service)
    def get_task(task_id):
        return jsonify(serialize_task(controller.get_task(g.user, task_id), overdue=True)), 200

    @blueprint.post('/tasks')
    @require_auth(auth_service)
    def create_task():
        task = controller.create_task(g.user, request.get_json())
        return jsonify(serialize_task(task)), 201

    @blueprint.put('/tasks/<int:task_id>')
    @require_auth(auth_service)
    def update_task(task_id):
        task = controller.update_task(g.user, task_id, request.get_json())
        return jsonify(serialize_task(task)), 200

    @blueprint.delete('/tasks/<int:task_id>')
    @require_auth(auth_service)
    def delete_task(task_id):
        return jsonify(controller.delete_task(g.user, task_id)), 200

    @blueprint.get('/tasks/search')
    @require_auth(auth_service)
    def search_tasks():
        return jsonify([serialize_task(task)
                        for task in controller.search_tasks(g.user, request.args)]), 200

    @blueprint.get('/tasks/stats')
    @require_auth(auth_service)
    def task_stats():
        return jsonify(controller.stats(g.user)), 200

    return blueprint
