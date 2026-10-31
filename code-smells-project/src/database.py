"""SQLite lifecycle and explicit, transactional schema/password migration."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA_VERSION = 1
TABLES = ("produtos", "usuarios", "pedidos", "itens_pedido")


class MigrationError(ValueError):
    """A safe diagnostic that never contains a row's credentials."""


def get_db(create=False):
    """Return the context-owned connection; never initialize or seed implicitly."""
    if "db" not in g:
        path = Path(current_app.config["DATABASE"]).resolve()
        if not create and not path.is_file():
            from .errors import ApiError

            raise ApiError("Banco não inicializado ou migração pendente", 503)
        connection = sqlite3.connect(
            path.as_uri() + ("?mode=rwc" if create else "?mode=rw"),
            uri=True, timeout=10, isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def init_app(app):
    @app.teardown_appcontext
    def close_db(error=None):
        connection = g.pop("db", None)
        if connection is not None:
            if connection.in_transaction:
                connection.rollback()
            connection.close()


@contextmanager
def transaction(db):
    """Own one write transaction, including inventory reads and decisions."""
    if db.in_transaction or getattr(db, "autocommit", None) is True:
        raise RuntimeError("A transação já possui um responsável")
    db.execute("BEGIN IMMEDIATE")
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise


def _tables(db):
    return {
        row[0]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def _version(db):
    if "schema_version" not in _tables(db):
        return None
    rows = db.execute("SELECT version FROM schema_version").fetchall()
    if len(rows) != 1:
        raise MigrationError("Versão de schema inválida")
    return rows[0][0]


def check_ready(db):
    """HTTP boundary check: never use an unversioned plaintext legacy schema."""
    from .errors import ApiError

    try:
        version = _version(db)
        tables = _tables(db)
        user_columns = {
            row[1] for row in db.execute("PRAGMA table_info(usuarios)")
        }
        ready = (
            version == SCHEMA_VERSION
            and set(TABLES).issubset(tables)
            and "ativo" in user_columns
        )
    except (sqlite3.DatabaseError, MigrationError):
        ready = False
    if not ready:
        raise ApiError("Banco não inicializado ou migração pendente", 503)


def _create_tables(db, suffix=""):
    # Table identifiers derive exclusively from these internal constant suffixes.
    if suffix not in {"", "_v1"}:
        raise ValueError("Sufixo de schema inválido")
    db.execute(f"""
        CREATE TABLE produtos{suffix} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT NOT NULL DEFAULT '',
            preco REAL NOT NULL CHECK (preco >= 0),
            estoque INTEGER NOT NULL CHECK (typeof(estoque) = 'integer' AND estoque >= 0),
            categoria TEXT NOT NULL DEFAULT 'geral',
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute(f"""
        CREATE TABLE usuarios{suffix} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL COLLATE NOCASE UNIQUE,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'cliente' CHECK (tipo IN ('cliente', 'admin')),
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
        )
    """)
    db.execute(f"""
        CREATE TABLE pedidos{suffix} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL REFERENCES usuarios{suffix}(id) ON DELETE RESTRICT,
            status TEXT NOT NULL DEFAULT 'pendente'
                CHECK (status IN ('pendente', 'aprovado', 'enviado', 'entregue', 'cancelado')),
            total REAL NOT NULL CHECK (total >= 0),
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute(f"""
        CREATE TABLE itens_pedido{suffix} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL REFERENCES pedidos{suffix}(id) ON DELETE RESTRICT,
            produto_id INTEGER NOT NULL REFERENCES produtos{suffix}(id) ON DELETE RESTRICT,
            quantidade INTEGER NOT NULL CHECK (typeof(quantidade) = 'integer' AND quantidade > 0),
            preco_unitario REAL NOT NULL CHECK (preco_unitario >= 0)
        )
    """)


def _mark_version(db):
    db.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    db.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
    db.execute("CREATE INDEX idx_pedidos_usuario ON pedidos(usuario_id)")
    db.execute("CREATE INDEX idx_itens_pedido ON itens_pedido(pedido_id)")
    db.execute("CREATE INDEX idx_itens_produto ON itens_pedido(produto_id)")


def initialize(db):
    """Create an empty current schema; never overwrite a legacy database."""
    db.execute("PRAGMA foreign_keys = ON")
    with transaction(db):
        tables = _tables(db)
        if tables:
            if _version(db) == SCHEMA_VERSION:
                check_ready(db)
                return False
            raise MigrationError("Banco existente: execute migrate-db; init-db não altera dados")
        _create_tables(db)
        _mark_version(db)
    return True


def _validate_legacy(db):
    tables = _tables(db)
    if tables != set(TABLES):
        raise MigrationError("Schema legado inesperado; migração cancelada sem alterar dados")
    custom_objects = db.execute("""
        SELECT COUNT(*) FROM sqlite_master
        WHERE type IN ('trigger', 'view') OR (type = 'index' AND name NOT LIKE 'sqlite_%')
    """).fetchone()[0]
    if custom_objects:
        raise MigrationError("Objetos personalizados exigem revisão; migração cancelada sem alterar dados")
    duplicates = db.execute(
        "SELECT COUNT(*) FROM (SELECT lower(email) FROM usuarios GROUP BY lower(email) HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    orphans = db.execute("""
        SELECT
          (SELECT COUNT(*) FROM pedidos p LEFT JOIN usuarios u ON u.id=p.usuario_id WHERE u.id IS NULL)
          + (SELECT COUNT(*) FROM itens_pedido i LEFT JOIN pedidos p ON p.id=i.pedido_id WHERE p.id IS NULL)
          + (SELECT COUNT(*) FROM itens_pedido i LEFT JOIN produtos p ON p.id=i.produto_id WHERE p.id IS NULL)
    """).fetchone()[0]
    if duplicates or orphans:
        raise MigrationError(
            f"Migração cancelada: {duplicates} emails duplicados e {orphans} vínculos órfãos; dados preservados"
        )


def migrate(db):
    """Migrate the confirmed legacy schema atomically, retaining IDs and sequences."""
    db.execute("PRAGMA foreign_keys = ON")
    with transaction(db):
        version = _version(db)
        if version == SCHEMA_VERSION:
            check_ready(db)
            return False
        if version is not None:
            raise MigrationError("Versão não suportada; banco preservado")
        _validate_legacy(db)
        sequences = {
            row[0]: row[1] for row in db.execute("SELECT name, seq FROM sqlite_sequence")
        }
        users = db.execute("SELECT * FROM usuarios ORDER BY id").fetchall()
        if any(
            not isinstance(user["senha"], str) or not user["senha"]
            or not isinstance(user["email"], str) or not user["email"]
            for user in users
        ):
            raise MigrationError("Credencial legada inválida; banco preservado")
        _create_tables(db, "_v1")
        try:
            db.execute("""
                INSERT INTO produtos_v1
                    (id, nome, descricao, preco, estoque, categoria, ativo, criado_em)
                SELECT id, nome, descricao, preco, estoque, categoria, ativo, criado_em
                FROM produtos
            """)
            for user in users:
                active = not (
                    user["email"].lower() == "admin@loja.com" and user["tipo"] == "admin"
                )
                db.execute("""
                    INSERT INTO usuarios_v1 (id, nome, email, senha, tipo, criado_em, ativo)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user["id"], user["nome"], user["email"],
                    generate_password_hash(user["senha"]), user["tipo"],
                    user["criado_em"], int(active),
                ))
            db.execute("""
                INSERT INTO pedidos_v1 (id, usuario_id, status, total, criado_em)
                SELECT id, usuario_id, status, total, criado_em FROM pedidos
            """)
            db.execute("""
                INSERT INTO itens_pedido_v1
                    (id, pedido_id, produto_id, quantidade, preco_unitario)
                SELECT id, pedido_id, produto_id, quantidade, preco_unitario
                FROM itens_pedido
            """)
        except sqlite3.IntegrityError as error:
            raise MigrationError("Dados legados violam restrições; migração cancelada, banco preservado") from error
        for table in reversed(TABLES):
            db.execute(f"DROP TABLE {table}")
        for table in TABLES:
            db.execute(f"ALTER TABLE {table}_v1 RENAME TO {table}")
            if table in sequences:
                updated = db.execute(
                    "UPDATE sqlite_sequence SET seq = MAX(seq, ?) WHERE name = ?",
                    (sequences[table], table),
                )
                if updated.rowcount == 0:
                    db.execute(
                        "INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)",
                        (table, sequences[table]),
                    )
        _mark_version(db)
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise MigrationError("Verificação de vínculos falhou; banco preservado")
    return True
