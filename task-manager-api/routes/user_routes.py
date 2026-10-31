"""User/login HTTP routes delegating to injected controllers."""

from flask import Blueprint, g, jsonify, request

from views.auth import require_auth
from views.tasks import serialize_task
from views.users import serialize_user


def create_user_blueprint(controller, auth_service):
    user_bp = Blueprint('users', __name__)
    authenticated = require_auth(auth_service)
    administrator = require_auth(auth_service, admin=True)

    @user_bp.get('/users')
    @administrator
    def get_users():
        return jsonify([
            {**serialize_user(user), 'task_count': count}
            for user, count in controller.list_users(g.user)
        ]), 200

    @user_bp.get('/users/<int:user_id>')
    @authenticated
    def get_user(user_id):
        user, tasks = controller.get_user(g.user, user_id)
        data = serialize_user(user)
        data['tasks'] = [serialize_task(task) for task in tasks]
        return jsonify(data), 200

    @user_bp.post('/users')
    def create_user():
        return jsonify(serialize_user(controller.create_user(request.get_json()))), 201

    @user_bp.put('/users/<int:user_id>')
    @authenticated
    def update_user(user_id):
        return jsonify(serialize_user(
            controller.update_user(g.user, user_id, request.get_json())
        )), 200

    @user_bp.delete('/users/<int:user_id>')
    @administrator
    def delete_user(user_id):
        controller.delete_user(g.user, user_id)
        return jsonify({'message': 'Usuário deletado com sucesso'}), 200

    @user_bp.get('/users/<int:user_id>/tasks')
    @authenticated
    def get_user_tasks(user_id):
        return jsonify([
            serialize_task(task, compact=True)
            for task in controller.get_user_tasks(g.user, user_id)
        ]), 200

    @user_bp.post('/login')
    def login():
        user, token = controller.login(request.get_json())
        return jsonify({
            'message': 'Login realizado com sucesso',
            'user': serialize_user(user),
            'token': token,
        }), 200

    return user_bp
