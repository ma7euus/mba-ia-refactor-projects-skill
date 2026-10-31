"""One public error boundary; exception details stay private."""
import sqlite3
from flask import jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message, self.status = message, status


def register_errors(app):
    @app.errorhandler(ApiError)
    def application_error(error):
        response = jsonify(erro=error.message, sucesso=False)
        if error.status == 401:
            response.headers["WWW-Authenticate"] = 'Basic realm="loja", charset="UTF-8"'
        return response, error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        messages = {400: "JSON ou requisição inválida", 404: "Recurso não encontrado",
                    405: "Método não permitido", 413: "Requisição muito grande", 415: "Envie um objeto JSON"}
        response = error.get_response()
        response.set_data(app.json.dumps({"erro": messages.get(error.code, "Requisição inválida"), "sucesso": False}))
        response.content_type = "application/json"
        return response

    @app.errorhandler(sqlite3.IntegrityError)
    def integrity_error(error):
        app.logger.warning("database_conflict type=%s", type(error).__name__)
        return jsonify(erro="Operação viola a integridade dos dados", sucesso=False), 409

    @app.errorhandler(Exception)
    def unexpected_error(error):
        # Exception text, SQL and traceback can include credentials or parameters.
        app.logger.error("request_failed type=%s", type(error).__name__)
        return jsonify(erro="Erro interno", sucesso=False), 500
