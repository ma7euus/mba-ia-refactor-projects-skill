"""Compose the existing Flask/SQLite stack using explicit dependencies."""
import logging
from flask import Flask
from flask_cors import CORS
from . import database
from .cli import register_cli
from .config import load_config
from .controllers.orders import OrderController
from .controllers.products import ProductController
from .controllers.system import SystemController
from .controllers.users import UserController
from .errors import register_errors
from .models.products import ProductModel
from .models.system import SystemModel
from .models.users import UserModel
from .services.admin import AdminService
from .services.orders import OrderService
from .services.products import ProductService
from .services.reports import ReportService
from .services.users import UserService
from .views.routes import register_routes


def create_app(overrides=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(load_config())
    app.config.update(overrides or {})
    app.logger.setLevel(logging.INFO)
    CORS(app)
    database.init_app(app)
    register_errors(app)
    register_cli(app)

    def build_controllers():
        db = database.get_db()
        database.check_ready(db)
        users = UserModel(db)
        return {
            "users": UserController(users, UserService(users)),
            "products": ProductController(ProductService(ProductModel(db))),
            "orders": OrderController(OrderService(db)),
            "system": SystemController(SystemModel(db), ReportService(db), AdminService(
                db, enable_reset=app.config["ENABLE_DB_RESET"], disposable=app.config["DISPOSABLE_DATABASE"]))}

    app.extensions["build_controllers"] = build_controllers
    register_routes(app)
    return app
