"""Explicit database preparation and local administrator provisioning."""

import sqlite3

import click
from werkzeug.security import generate_password_hash

from .database import MigrationError, check_ready, get_db, initialize, migrate, transaction
from .errors import ApiError


def _run_database_command(operation, create=False):
    try:
        return operation(get_db(create=create))
    except MigrationError as error:
        raise click.ClickException(str(error)) from error
    except ApiError as error:
        raise click.ClickException(str(error)) from error
    except sqlite3.DatabaseError as error:
        raise click.ClickException("Operação não concluída; nenhuma alteração foi confirmada") from error


def _valid_identity(name, email, password):
    if not isinstance(name, str) or not name.strip() or len(name) > 200:
        raise click.ClickException("Nome inválido")
    if not isinstance(email, str) or "@" not in email or len(email) > 254:
        raise click.ClickException("Email inválido")
    if not isinstance(password, str) or not password or len(password) > 1024:
        raise click.ClickException("Senha inválida")


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        changed = _run_database_command(initialize, create=True)
        click.echo("Banco inicializado vazio" if changed else "Banco já inicializado")

    @app.cli.command("migrate-db")
    def migrate_db():
        changed = _run_database_command(migrate)
        click.echo("Migração concluída; redefina a senha do administrador de demonstração antes de usá-lo" if changed else "Banco já migrado")

    @app.cli.command("create-admin")
    @click.option("--nome", prompt=True)
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(nome, email, password):
        _valid_identity(nome, email, password)

        def create(db):
            check_ready(db)
            with transaction(db):
                if db.execute("SELECT id FROM usuarios WHERE email = ?", (email,)).fetchone():
                    raise MigrationError("Email já cadastrado; use set-password para redefinir a senha")
                db.execute(
                    "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, 'admin')",
                    (nome.strip(), email.strip(), generate_password_hash(password)),
                )

        _run_database_command(create)
        click.echo("Administrador criado")

    @app.cli.command("set-password")
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def set_password(email, password):
        _valid_identity("Redefinição local", email, password)

        def update(db):
            check_ready(db)
            with transaction(db):
                changed = db.execute(
                    "UPDATE usuarios SET senha = ?, ativo = 1 WHERE email = ?",
                    (generate_password_hash(password), email.strip()),
                )
                if changed.rowcount != 1:
                    raise MigrationError("Usuário não encontrado; banco preservado")

        _run_database_command(update)
        click.echo("Senha redefinida e conta ativada")
