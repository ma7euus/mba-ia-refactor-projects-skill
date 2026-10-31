"""Composition root and stable launcher; importing this module never creates tables."""

import os

import click
from flask import Flask
from flask_cors import CORS

from config import configuration
from controllers.categories import CategoryController
from controllers.reports import ReportController
from controllers.tasks import TaskController
from controllers.users import UserController
from database import configure_database, db
from errors import AppError, register_errors
from models.user import User
from routes.report_routes import create_report_blueprint
from routes.task_routes import create_task_blueprint
from routes.user_routes import create_user_blueprint
from services.authentication import AuthService
from services.user_validation import validate_email, validate_name, validate_password
from utils.helpers import utc_now


def create_app(config=None):
    application = Flask(__name__)
    application.config.update(configuration())
    if config:
        application.config.update(config)
    configure_database(application)
    CORS(application, origins=application.config['CORS_ORIGINS'])

    auth = AuthService(db.session, session_seconds=application.config['SESSION_TTL_SECONDS'])
    users = UserController(db.session, auth)
    tasks = TaskController(db.session)
    categories = CategoryController(db.session)
    reports = ReportController(db.session)
    application.register_blueprint(create_user_blueprint(users, auth))
    application.register_blueprint(create_task_blueprint(tasks, auth))
    application.register_blueprint(create_report_blueprint(reports, categories, auth))
    register_errors(application, db.session)
    application.extensions['task_manager_auth'] = auth

    @application.get('/')
    def index():
        return {'message': 'Task Manager API', 'version': '1.0'}

    @application.get('/health')
    def health():
        return {'status': 'ok', 'timestamp': str(utc_now())}

    @application.cli.command('init-db')
    def init_db():
        """Create missing tables (including sessions), preserving existing rows."""
        db.create_all()
        click.echo('Schema inicializado; dados existentes preservados.')

    @application.cli.command('create-admin')
    def create_admin():
        """Provision a NEW admin using ADMIN_NAME, ADMIN_EMAIL and ADMIN_PASSWORD."""
        try:
            name = validate_name(os.environ.get('ADMIN_NAME'))
            email = validate_email(os.environ.get('ADMIN_EMAIL'))
            password = validate_password(os.environ.get('ADMIN_PASSWORD'))
        except AppError:
            raise click.ClickException('Defina ADMIN_NAME, ADMIN_EMAIL e ADMIN_PASSWORD válidos.') from None
        if db.session.scalar(db.select(User).where(User.email == email)):
            raise click.ClickException('Email já cadastrado; nenhuma conta foi alterada.')
        user = User(name=name, email=email, role='admin', active=True)
        user.set_password(password)
        try:
            db.session.add(user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise click.ClickException('Não foi possível criar o administrador.') from None
        click.echo('Administrador criado.')

    return application


app = create_app()

if __name__ == '__main__':
    app.run(host=app.config['HOST'], port=app.config['PORT'], debug=app.config['DEBUG'])
