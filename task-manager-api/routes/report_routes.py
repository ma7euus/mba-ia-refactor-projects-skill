from flask import Blueprint, g, jsonify, request

from views.auth import require_auth
from views.categories import serialize_category


def create_report_blueprint(report_controller, category_controller, auth_service):
    blueprint = Blueprint('reports', __name__)

    @blueprint.get('/reports/summary')
    @require_auth(auth_service, admin=True)
    def summary_report():
        return jsonify(report_controller.summary(g.user)), 200

    @blueprint.get('/reports/user/<int:user_id>')
    @require_auth(auth_service)
    def user_report(user_id):
        return jsonify(report_controller.user_report(g.user, user_id)), 200

    @blueprint.get('/categories')
    @require_auth(auth_service)
    def get_categories():
        return jsonify([serialize_category(category, count)
                        for category, count in category_controller.list_categories(g.user)]), 200

    @blueprint.post('/categories')
    @require_auth(auth_service, admin=True)
    def create_category():
        category = category_controller.create_category(g.user, request.get_json())
        return jsonify(serialize_category(category)), 201

    @blueprint.put('/categories/<int:cat_id>')
    @require_auth(auth_service, admin=True)
    def update_category(cat_id):
        category = category_controller.update_category(g.user, cat_id, request.get_json())
        return jsonify(serialize_category(category)), 200

    @blueprint.delete('/categories/<int:cat_id>')
    @require_auth(auth_service, admin=True)
    def delete_category(cat_id):
        return jsonify(category_controller.delete_category(g.user, cat_id)), 200

    return blueprint
