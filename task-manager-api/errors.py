"""The application's single HTTP error boundary."""

from flask import jsonify
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException


class AppError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def register_errors(app, session):
    @app.errorhandler(AppError)
    def application_error(error):
        session.rollback()
        return jsonify(error=error.message), error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        session.rollback()
        messages = {
            400: 'Dados inválidos', 404: 'Recurso não encontrado',
            405: 'Método não permitido', 413: 'Corpo da requisição muito grande',
            415: 'Envie um objeto JSON',
        }
        status = 400 if error.code == 415 else error.code
        response = error.get_response()
        response.data = app.json.dumps({'error': messages.get(error.code, 'Requisição inválida')})
        response.content_type = 'application/json'
        response.status_code = status
        return response

    @app.errorhandler(IntegrityError)
    def integrity_error(error):
        session.rollback()
        return jsonify(error='Operação em conflito com os dados existentes'), 409

    @app.errorhandler(Exception)
    def unexpected_error(error):
        session.rollback()
        # Exception text and SQL parameters can contain passwords and tokens.
        app.logger.error('Falha inesperada: %s', type(error).__name__)
        return jsonify(error='Erro interno'), 500
