"""Validate the current checkout over real HTTP using disposable SQLite files.

Run from the project: .venv/bin/python tests/run_validation.py
stdout is sanitized JSON evidence; unittest progress is sent to stderr.
"""

import base64
from concurrent.futures import ThreadPoolExecutor
import contextlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from werkzeug.security import check_password_hash, generate_password_hash


PASSWORD = "Only-synthetic-validation-42"
PASSWORD_HASH = generate_password_hash(PASSWORD)
ADMIN = ("validation.admin@example.test", PASSWORD)
CLIENT = ("validation.client@example.test", PASSWORD)
OTHER = ("validation.other@example.test", PASSWORD)
CHECKS = []
BOOT_LOGS = []
OPERATIONS = set()
EXPECTED_OPERATIONS = {
    ("GET", "/"), ("GET", "/health"), ("GET", "/produtos"),
    ("GET", "/produtos/busca"), ("GET", "/produtos/<int:id>"),
    ("POST", "/produtos"), ("PUT", "/produtos/<int:id>"),
    ("DELETE", "/produtos/<int:id>"), ("GET", "/usuarios"),
    ("GET", "/usuarios/<int:id>"), ("POST", "/usuarios"), ("POST", "/login"),
    ("POST", "/pedidos"), ("GET", "/pedidos"),
    ("GET", "/pedidos/usuario/<int:usuario_id>"),
    ("PUT", "/pedidos/<int:pedido_id>/status"),
    ("GET", "/relatorios/vendas"), ("POST", "/admin/query"),
    ("POST", "/admin/reset-db"),
}


def connect(path):
    db = sqlite3.connect(path, isolation_level=None, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


class Server:
    def __init__(self, database, **settings):
        self.database = database
        self.settings = settings

    def __enter__(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.url = f"http://127.0.0.1:{port}"
        self.log = tempfile.TemporaryFile(mode="w+")
        env = dict(os.environ, DATABASE_PATH=str(self.database), HOST="127.0.0.1",
                   PORT=str(port), ENABLE_DB_RESET="true", DISPOSABLE_DATABASE="true",
                   PYTHONDONTWRITEBYTECODE="1")
        env.update(self.settings)
        self.process = subprocess.Popen([sys.executable, "app.py"], cwd=ROOT, env=env,
                                        stdout=self.log, stderr=self.log)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                self.__exit__(None, None, None)
                raise AssertionError("Current application exited before HTTP readiness")
            try:
                self.request("GET", "/")
                return self
            except (OSError, urllib.error.URLError):
                time.sleep(0.05)
        self.__exit__(None, None, None)
        raise AssertionError("Current application did not become ready in 15 seconds")

    def __exit__(self, *args):
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        self.log.seek(0)
        # Never include request credentials, payloads or a raw traceback in evidence.
        for line in self.log.read().splitlines():
            if "Running on" in line or "Serving Flask" in line or "Debug mode" in line:
                BOOT_LOGS.append(line)
        self.log.close()

    def request(self, method, path, payload=None, auth=None, raw=None):
        headers = {"Content-Type": "application/json"}
        if auth:
            encoded = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        data = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
        request = urllib.request.Request(self.url + path, data=data, headers=headers, method=method)
        try:
            response = urllib.request.urlopen(request, timeout=15)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            body = json.loads(response.read())
            return response.code, body


class HttpValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from src.database import initialize
        cls.temp = tempfile.TemporaryDirectory(prefix="loja-current-http-")
        cls.path = Path(cls.temp.name) / "loja.db"
        with contextlib.closing(connect(cls.path)) as db:
            initialize(db)
        cls.server_context = Server(cls.path)
        cls.server = cls.server_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.server_context.__exit__(None, None, None)
        cls.temp.cleanup()

    def setUp(self):
        with contextlib.closing(connect(self.path)) as db:
            db.execute("BEGIN IMMEDIATE")
            for table in ("itens_pedido", "pedidos", "produtos", "usuarios"):
                db.execute(f"DELETE FROM {table}")
            db.execute("DELETE FROM sqlite_sequence")
            for name, email, role in (("Admin Validation", ADMIN[0], "admin"),
                                     ("Client Validation", CLIENT[0], "cliente"),
                                     ("Other Validation", OTHER[0], "cliente")):
                db.execute("INSERT INTO usuarios(nome,email,senha,tipo,ativo) VALUES(?,?,?,?,1)",
                           (name, email, PASSWORD_HASH, role))
            products = [("Notebook", 5999.99, 10), ("Mouse", 89.90, 50)]
            products += [(f"Fixture {n}", 25.0, 12) for n in range(3, 11)]
            db.executemany("INSERT INTO produtos(nome,descricao,preco,estoque,categoria) VALUES(?,?,?,?,?)",
                           [(name, "Fixture explícita", price, stock, "informatica")
                            for name, price, stock in products])
            db.commit()

    def query(self, sql, params=()):
        with contextlib.closing(connect(self.path)) as db:
            return [dict(row) for row in db.execute(sql, params).fetchall()]

    def snapshot(self):
        return {table: self.query(f"SELECT * FROM {table} ORDER BY id")
                for table in ("usuarios", "produtos", "pedidos", "itens_pedido")}

    def call(self, label, method, path, payload=None, expected=200, auth=None, route=None, raw=None):
        status, body = self.server.request(method, path, payload, auth=auth, raw=raw)
        CHECKS.append({"case": label, "method": method, "route": route or path.split("?")[0],
                       "expected_status": expected, "observed_status": status, "passed": status == expected})
        self.assertEqual(status, expected, label)
        self.assert_public(body)
        if expected < 300:
            OPERATIONS.add((method, route or path.split("?")[0]))
        return body

    def assert_public(self, value):
        if isinstance(value, dict):
            for key, child in value.items():
                self.assertNotIn(key.lower(), {"senha", "password", "secret_key", "password_hash", "db_path"})
                self.assert_public(child)
        elif isinstance(value, list):
            for child in value:
                self.assert_public(child)
        elif isinstance(value, str):
            self.assertNotIn(PASSWORD, value)
            self.assertNotIn(PASSWORD_HASH, value)

    def test_01_baseline_39_cases_with_approved_corrections(self):
        start = len(CHECKS)
        self.assertEqual(self.call("P1-01 raiz", "GET", "/")["versao"], "1.0.0")
        health = self.call("P1-02 health", "GET", "/health")
        self.assertEqual(health["counts"], {"produtos": 10, "usuarios": 3, "pedidos": 0})
        self.assertEqual(len(self.call("P1-03 catálogo", "GET", "/produtos")["dados"]), 10)
        self.call("P1-04 detalhe produto", "GET", "/produtos/2", route="/produtos/<int:id>")
        self.call("P1-05 produto ausente", "GET", "/produtos/999999", expected=404)
        found = self.call("P1-06 busca", "GET", "/produtos/busca?q=Mouse&categoria=informatica&preco_min=80&preco_max=100")
        self.assertEqual([row["id"] for row in found["dados"]], [2])
        self.call("P1-07 preço textual", "GET", "/produtos/busca?preco_min=abc", expected=400)
        self.assertEqual(len(self.call("P1-08 usuários", "GET", "/usuarios", auth=ADMIN)["dados"]), 3)
        self.call("P1-09 detalhe usuário", "GET", "/usuarios/1", auth=ADMIN, route="/usuarios/<int:id>")
        self.call("P1-10 usuário ausente", "GET", "/usuarios/999999", auth=ADMIN, expected=404)
        signup = {"nome": "Pessoa Baseline", "email": "baseline.validation@example.test", "senha": PASSWORD}
        user_id = self.call("P1-11 cadastro", "POST", "/usuarios", signup, expected=201)["dados"]["id"]
        stored = self.query("SELECT senha FROM usuarios WHERE id=?", (user_id,))[0]["senha"]
        self.assertNotEqual(stored, PASSWORD)
        self.assertTrue(check_password_hash(stored, PASSWORD))
        self.call("P1-12 cadastro incompleto", "POST", "/usuarios", {"nome": "Incompleto"}, expected=400)
        self.call("P1-13 login", "POST", "/login", {"email": signup["email"], "senha": PASSWORD})
        self.call("P1-14 login incorreto", "POST", "/login", {"email": signup["email"], "senha": "invalid"}, expected=401)
        self.call("P1-15 login incompleto", "POST", "/login", {}, expected=400)
        product = {"nome": "Produto Baseline", "descricao": "Registro descartável", "preco": 25.0, "estoque": 12, "categoria": "geral"}
        product_id = self.call("P1-16 criar produto", "POST", "/produtos", product, 201, ADMIN)["dados"]["id"]
        updated = dict(product, nome="Produto Editado", preco=27.5, estoque=15)
        self.call("P1-17 editar produto", "PUT", f"/produtos/{product_id}", updated, auth=ADMIN, route="/produtos/<int:id>")
        self.assertEqual(self.query("SELECT nome,preco,estoque FROM produtos WHERE id=?", (product_id,))[0],
                         {"nome": "Produto Editado", "preco": 27.5, "estoque": 15})
        self.call("P1-18 preço negativo", "POST", "/produtos", dict(product, preco=-1), 400, ADMIN)
        self.call("P1-19 preço textual corrigido", "POST", "/produtos", dict(product, preco="abc"), 400, ADMIN)
        self.call("P1-20 apóstrofo", "POST", "/produtos", dict(product, nome="Caderno d'água"), 201, ADMIN)
        self.call("P1-21 editar ausente", "PUT", "/produtos/999999", product, 404, ADMIN)
        order = {"usuario_id": user_id, "itens": [{"produto_id": 2, "quantidade": 2}]}
        order_id = self.call("P1-22 criar pedido", "POST", "/pedidos", order, 201, ADMIN)["dados"]["pedido_id"]
        self.assertEqual(self.query("SELECT estoque FROM produtos WHERE id=2")[0]["estoque"], 48)
        self.assertEqual(self.query("SELECT total FROM pedidos WHERE id=?", (order_id,))[0]["total"], 179.8)
        self.assertEqual(self.query("SELECT quantidade FROM itens_pedido WHERE pedido_id=?", (order_id,))[0]["quantidade"], 2)
        self.call("P1-23 listar pedidos", "GET", "/pedidos", auth=ADMIN)
        self.call("P1-24 pedidos usuário", "GET", f"/pedidos/usuario/{user_id}", auth=ADMIN, route="/pedidos/usuario/<int:usuario_id>")
        self.call("P1-25 aprovar pedido", "PUT", f"/pedidos/{order_id}/status", {"status": "aprovado"}, auth=ADMIN, route="/pedidos/<int:pedido_id>/status")
        self.assertEqual(self.query("SELECT status FROM pedidos WHERE id=?", (order_id,))[0]["status"], "aprovado")
        self.call("P1-26 status inválido", "PUT", f"/pedidos/{order_id}/status", {"status": "inventado"}, 400, ADMIN)
        self.call("P1-27 status ausente corrigido", "PUT", "/pedidos/999999/status", {"status": "enviado"}, 404, ADMIN)
        report = self.call("P1-28 relatório", "GET", "/relatorios/vendas", auth=ADMIN)["dados"]
        self.assertEqual(report, {"total_pedidos": 1, "faturamento_bruto": 179.8, "desconto_aplicavel": 0,
                                  "faturamento_liquido": 179.8, "pedidos_pendentes": 0,
                                  "pedidos_aprovados": 1, "pedidos_cancelados": 0, "ticket_medio": 179.8})
        before = self.snapshot()
        self.call("P1-29 estoque insuficiente", "POST", "/pedidos", dict(order, itens=[{"produto_id": 2, "quantidade": 49}]), 400, ADMIN)
        self.call("P1-30 produto inexistente", "POST", "/pedidos", dict(order, itens=[{"produto_id": 999999, "quantidade": 1}]), 400, ADMIN)
        self.call("P1-31 sem itens", "POST", "/pedidos", dict(order, itens=[]), 400, ADMIN)
        self.call("P1-32 quantidade negativa corrigida", "POST", "/pedidos", dict(order, itens=[{"produto_id": 2, "quantidade": -2}]), 400, ADMIN)
        self.call("P1-33 usuário inexistente corrigido", "POST", "/pedidos", dict(order, usuario_id=999999), 404, ADMIN)
        self.assertEqual(self.snapshot(), before)
        self.call("P1-34 excluir produto", "DELETE", f"/produtos/{product_id}", auth=ADMIN, route="/produtos/<int:id>")
        self.assertFalse(self.query("SELECT id FROM produtos WHERE id=?", (product_id,)))
        self.call("P1-35 exclusão repetida", "DELETE", f"/produtos/{product_id}", auth=ADMIN, expected=404)
        self.call("P1-36 exclusão ausente", "DELETE", "/produtos/999999", auth=ADMIN, expected=404)
        self.call("P1-37 consulta anônima corrigida", "POST", "/admin/query", {"sql": "SELECT COUNT(*) AS total FROM produtos"}, expected=401)
        self.call("P1-38 consulta incompleta", "POST", "/admin/query", {}, 400, ADMIN)
        before = self.snapshot()
        self.call("P1-39 reset anônimo corrigido", "POST", "/admin/reset-db", {}, expected=401)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(CHECKS) - start, 39)

    def test_02_authorization_and_bounded_admin(self):
        product = {"nome": "Restricted", "preco": 10, "estoque": 3}
        before = self.snapshot()
        protected = [("GET", "/usuarios", None), ("GET", "/pedidos", None),
                     ("GET", "/relatorios/vendas", None), ("POST", "/produtos", product),
                     ("PUT", "/produtos/2", product), ("DELETE", "/produtos/2", None),
                     ("PUT", "/pedidos/1/status", {"status": "aprovado"}),
                     ("POST", "/admin/query", {"sql": "SELECT COUNT(*) AS total FROM produtos"}),
                     ("POST", "/admin/reset-db", {"confirmacao": "RESET"})]
        for method, path, data in protected:
            for identity, expected in ((None, 401), (CLIENT, 403), ((ADMIN[0], "invalid"), 401)):
                with self.subTest(method=method, path=path, expected=expected):
                    self.call("permission boundary", method, path, data, expected, identity)
        self.call("cross-user detalhe", "GET", "/usuarios/3", auth=CLIENT, expected=403)
        self.call("cross-user pedidos", "GET", "/pedidos/usuario/3", auth=CLIENT, expected=403)
        self.call("cross-user criação", "POST", "/pedidos", {"usuario_id": 3, "itens": [{"produto_id": 2, "quantidade": 1}]}, 403, CLIENT)
        self.assertEqual(self.snapshot(), before)
        self.call("own user detail", "GET", "/usuarios/2", auth=CLIENT, route="/usuarios/<int:id>")
        self.call("own order listing", "GET", "/pedidos/usuario/2", auth=CLIENT, route="/pedidos/usuario/<int:usuario_id>")
        self.call("own order creation", "POST", "/pedidos", {"usuario_id": 2, "itens": [{"produto_id": 2, "quantidade": 1}]}, 201, CLIENT)
        for table in ("produtos", "usuarios", "pedidos", "itens_pedido"):
            response = self.call("bounded admin count", "POST", "/admin/query", {"sql": f"SELECT COUNT(*) AS total FROM {table}"}, auth=ADMIN)
            self.assertEqual(response["dados"][0]["total"], self.query(f"SELECT COUNT(*) AS total FROM {table}")[0]["total"])
        for sql in ("SELECT senha FROM usuarios", "DELETE FROM produtos", "SELECT COUNT(*) AS total FROM produtos; DELETE FROM usuarios", "PRAGMA table_info(usuarios)"):
            self.call("arbitrary SQL refused", "POST", "/admin/query", {"sql": sql}, 400, ADMIN)
        before = self.snapshot()
        self.call("reset confirmation required", "POST", "/admin/reset-db", {}, 400, ADMIN)
        self.assertEqual(self.snapshot(), before)
        self.call("authorized disposable reset", "POST", "/admin/reset-db", {"confirmacao": "RESET"}, auth=ADMIN)
        self.assertTrue(all(not rows for rows in self.snapshot().values()))
        self.assertEqual(self.call("no implicit reseed after reset", "GET", "/produtos")["dados"], [])

    def test_03_invalid_shapes_types_and_quantities_preserve_state(self):
        before = self.snapshot()
        for payload in ([], None, "text", True, 2):
            self.call("invalid JSON structure", "POST", "/usuarios", expected=400, raw=json.dumps(payload).encode())
        self.call("malformed JSON", "POST", "/usuarios", expected=400, raw=b"{broken")
        product = {"nome": "Product", "preco": 10, "estoque": 3}
        for field, values in (("preco", [True, "abc", None, -1, float("inf"), float("nan")]),
                              ("estoque", [True, "3", None, -1, 1.5]),
                              ("nome", [True, None, {}, "x"]),
                              ("categoria", ["unknown", None, []])):
            for value in values:
                with self.subTest(field=field, value_type=type(value).__name__):
                    self.call("invalid product field", "POST", "/produtos", dict(product, **{field: value}), 400, ADMIN)
                    self.call("invalid product edit", "PUT", "/produtos/2", dict(product, **{field: value}), 400, ADMIN)
        for value in (0, -1, 1.5, True, None, "2"):
            order = {"usuario_id": 2, "itens": [{"produto_id": 2, "quantidade": value}]}
            self.call("invalid order quantity", "POST", "/pedidos", order, 400, CLIENT)
        for items in ({"produto_id": 2}, "text", [None], [True], [{}]):
            self.call("invalid order items", "POST", "/pedidos", {"usuario_id": 2, "itens": items}, 400, CLIENT)
        for user_id in (None, True, "2", 0, -1):
            self.call("invalid owner ID before authorization", "POST", "/pedidos",
                      {"usuario_id": user_id, "itens": [{"produto_id": 2, "quantidade": 1}]}, 400, CLIENT)
        repeated = {"usuario_id": 2, "itens": [{"produto_id": 2, "quantidade": 30}, {"produto_id": 2, "quantidade": 30}]}
        self.call("duplicate products aggregate stock", "POST", "/pedidos", repeated, 400, CLIENT)
        self.call("public role escalation", "POST", "/usuarios", {"nome": "Escalation", "email": "escalation@example.test", "senha": PASSWORD, "tipo": "admin"}, expected=400)
        self.call("literal SQL login", "POST", "/login", {"email": "' OR 1=1 --", "senha": PASSWORD}, expected=401)
        for query in ("preco_min=nan", "preco_max=inf", "preco_min=-1", "preco_min=100&preco_max=1"):
            self.call("invalid search range", "GET", "/produtos/busca?" + query, expected=400)
        huge_id = 9223372036854775808
        for method, path, data, identity in (
            ("GET", f"/produtos/{huge_id}", None, None),
            ("GET", f"/usuarios/{huge_id}", None, ADMIN),
            ("GET", f"/pedidos/usuario/{huge_id}", None, ADMIN),
            ("PUT", f"/pedidos/{huge_id}/status", {"status": "aprovado"}, ADMIN),
        ):
            self.call("out of SQLite range path ID", method, path, data, 400, identity)
        self.assertEqual(self.snapshot(), before)

    def test_04_rollback_references_and_concurrent_stock(self):
        with contextlib.closing(connect(self.path)) as db:
            db.execute("CREATE TRIGGER fail_second_item BEFORE INSERT ON itens_pedido WHEN NEW.produto_id=3 BEGIN SELECT RAISE(ABORT,'synthetic fault'); END")
        before = self.snapshot()
        order = {"usuario_id": 2, "itens": [{"produto_id": 2, "quantidade": 2}, {"produto_id": 3, "quantidade": 1}]}
        try:
            response = self.call("rollback on second item integrity failure", "POST", "/pedidos", order, 409, ADMIN)
            self.assertNotIn("synthetic fault", json.dumps(response))
            self.assertEqual(self.snapshot(), before)
        finally:
            with contextlib.closing(connect(self.path)) as db:
                db.execute("DROP TRIGGER fail_second_item")
        self.call("successful request after rollback", "POST", "/pedidos", order, 201, ADMIN)
        self.call("referenced product restrict", "DELETE", "/produtos/2", auth=ADMIN, expected=409)
        self.assertEqual(self.query("PRAGMA foreign_key_check"), [])
        with contextlib.closing(connect(self.path)) as db:
            db.execute("UPDATE produtos SET estoque=1 WHERE id=10")
        competing = {"usuario_id": 2, "itens": [{"produto_id": 10, "quantidade": 1}]}
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.server.request, "POST", "/pedidos", competing, CLIENT) for _ in range(2)]
            results = [future.result() for future in futures]
        self.assertEqual(sorted(status for status, _ in results), [201, 400])
        self.assertEqual(self.query("SELECT estoque FROM produtos WHERE id=10")[0]["estoque"], 0)
        self.assertEqual(self.query("SELECT SUM(quantidade) AS q FROM itens_pedido WHERE produto_id=10")[0]["q"], 1)
        CHECKS.append({"case": "concurrent stock reservation", "passed": True, "observed_statuses": sorted(status for status, _ in results)})

    def test_05_reset_disabled_and_missing_database_boot(self):
        before = self.snapshot()
        with Server(self.path, ENABLE_DB_RESET="false") as restricted:
            status, _ = restricted.request("POST", "/admin/reset-db", {"confirmacao": "RESET"}, ADMIN)
            self.assertEqual(status, 403)
        with Server(self.path, DISPOSABLE_DATABASE="false") as restricted:
            status, _ = restricted.request("POST", "/admin/reset-db", {"confirmacao": "RESET"}, ADMIN)
            self.assertEqual(status, 403)
        self.assertEqual(self.snapshot(), before)
        with tempfile.TemporaryDirectory(prefix="loja-no-bootstrap-") as folder:
            missing = Path(folder) / "missing.db"
            with Server(missing) as server:
                self.assertFalse(missing.exists())
                status, body = server.request("GET", "/health")
                self.assertEqual(status, 503)
                self.assert_public(body)
                self.assertFalse(missing.exists())
        CHECKS.append({"case": "boot without automatic database or seed; restricted reset", "passed": True})

    def test_06_runtime_operation_inventory(self):
        from src import create_app
        app = create_app({"DATABASE": str(self.path), "TESTING": True})
        actual = {(method, rule.rule) for rule in app.url_map.iter_rules()
                  if rule.endpoint != "static" for method in rule.methods - {"HEAD", "OPTIONS"}}
        self.assertEqual(actual, EXPECTED_OPERATIONS)
        CHECKS.append({"case": "runtime route inventory", "passed": True, "operations": len(actual)})


LEGACY_SCHEMA = """
CREATE TABLE produtos(id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,descricao TEXT,preco REAL,estoque INTEGER,categoria TEXT,ativo INTEGER DEFAULT 1,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE usuarios(id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,email TEXT,senha TEXT,tipo TEXT DEFAULT 'cliente',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE pedidos(id INTEGER PRIMARY KEY AUTOINCREMENT,usuario_id INTEGER,status TEXT DEFAULT 'pendente',total REAL,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE itens_pedido(id INTEGER PRIMARY KEY AUTOINCREMENT,pedido_id INTEGER,produto_id INTEGER,quantidade INTEGER,preco_unitario REAL);
"""


class DomainValidation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="loja-domain-")
        self.path = Path(self.temp.name) / "fixture.db"
        self.db = connect(self.path)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def legacy_fixture(self, orphan=False, reordered=False):
        schema = LEGACY_SCHEMA
        if reordered:
            schema = schema.replace("preco REAL,estoque INTEGER", "estoque INTEGER,preco REAL")
            schema = schema.replace("status TEXT DEFAULT 'pendente',total REAL", "total REAL,status TEXT DEFAULT 'pendente'")
            schema = schema.replace("quantidade INTEGER,preco_unitario REAL", "preco_unitario REAL,quantidade INTEGER")
        self.db.executescript(schema)
        self.db.execute("INSERT INTO produtos(id,nome,descricao,preco,estoque,categoria) VALUES(7,'Legacy product','Legacy',10,5,'geral')")
        for user_id, name, email, role in ((4, "Legacy client", CLIENT[0], "cliente"), (5, "Legacy Admin", "admin@loja.com", "admin")):
            self.db.execute("INSERT INTO usuarios(id,nome,email,senha,tipo) VALUES(?,?,?,?,?)", (user_id, name, email, PASSWORD, role))
        self.db.execute("INSERT INTO pedidos(id,usuario_id,total,status) VALUES(9,?,20,'aprovado')", (999 if orphan else 4,))
        self.db.execute("INSERT INTO itens_pedido(id,pedido_id,produto_id,quantidade,preco_unitario) VALUES(11,9,7,2,10)")
        # sqlite_sequence may exceed MAX(id); migration must retain that history.
        self.db.execute("INSERT INTO usuarios(id,nome,email,senha,tipo) VALUES(99,'Deleted','deleted@example.test',?,'cliente')", (PASSWORD,))
        self.db.execute("DELETE FROM usuarios WHERE id=99")

    def test_07_legacy_migration_idempotency_ids_and_admin_reset(self):
        from src.database import migrate, check_ready
        from src import create_app
        self.legacy_fixture()
        original = dict(self.db.execute("SELECT * FROM pedidos WHERE id=9").fetchone())
        migrate(self.db)
        check_ready(self.db)
        self.assertEqual(dict(self.db.execute("SELECT * FROM pedidos WHERE id=9").fetchone()), original)
        stored = self.db.execute("SELECT senha FROM usuarios WHERE id=4").fetchone()[0]
        self.assertTrue(check_password_hash(stored, PASSWORD))
        self.assertEqual(self.db.execute("SELECT ativo FROM usuarios WHERE id=5").fetchone()[0], 0)
        self.assertEqual(self.db.execute("SELECT seq FROM sqlite_sequence WHERE name='usuarios'").fetchone()[0], 99)
        self.assertFalse(self.db.execute("PRAGMA foreign_key_check").fetchall())
        migrate(self.db)
        self.assertEqual(self.db.execute("SELECT senha FROM usuarios WHERE id=4").fetchone()[0], stored)
        app = create_app({"DATABASE": str(self.path), "TESTING": True})
        with app.test_client() as client:
            result = client.post("/login", json={"email": CLIENT[0], "senha": PASSWORD})
            self.assertEqual(result.status_code, 200)
            result = client.post("/login", json={"email": "admin@loja.com", "senha": PASSWORD})
            self.assertEqual(result.status_code, 401)
        reset = app.test_cli_runner().invoke(args=["set-password", "--email", "admin@loja.com", "--password", PASSWORD + "-reset"])
        self.assertEqual(reset.exit_code, 0, "set-password CLI failed")
        self.assertNotIn(PASSWORD, reset.output)
        with app.test_client() as client:
            result = client.post("/login", json={"email": "admin@loja.com", "senha": PASSWORD + "-reset"})
            self.assertEqual(result.status_code, 200)
        CHECKS.append({"case": "legacy migration preserves IDs/history/password login; idempotent; admin reset", "passed": True})

    def test_08_migration_orphan_abort_without_writes(self):
        from src.database import migrate
        self.legacy_fixture(orphan=True)
        before = list(self.db.iterdump())
        with self.assertRaises(Exception):
            migrate(self.db)
        self.assertEqual(list(self.db.iterdump()), before)
        self.assertFalse(self.db.in_transaction)
        CHECKS.append({"case": "orphan migration abort preserves all legacy data", "passed": True})

    def test_08b_long_legacy_password_survives_migration(self):
        from src.database import migrate
        from src import create_app
        self.legacy_fixture()
        long_password = PASSWORD * 40
        self.db.execute("UPDATE usuarios SET senha=? WHERE id=4", (long_password,))
        migrate(self.db)
        app = create_app({"DATABASE": str(self.path), "TESTING": True})
        with app.test_client() as client:
            result = client.post("/login", json={"email": CLIENT[0], "senha": long_password})
            self.assertEqual(result.status_code, 200)
            self.assertNotIn(long_password, result.get_data(as_text=True))
        CHECKS.append({"case": "long legacy password still authenticates after migration", "passed": True})

    def test_08c_unexpected_failure_sanitizes_response_and_logs(self):
        from src import create_app
        app = create_app({"DATABASE": str(self.path), "TESTING": True})

        @app.get("/__controlled_failure")
        def controlled_failure():
            raise RuntimeError("Synthetic private diagnostic: " + PASSWORD)

        with self.assertLogs(app.logger, level="ERROR") as captured:
            with app.test_client() as client:
                result = client.get("/__controlled_failure")
        self.assertEqual(result.status_code, 500)
        self.assertEqual(result.get_json()["erro"], "Erro interno")
        self.assertNotIn(PASSWORD, result.get_data(as_text=True))
        self.assertNotIn(PASSWORD, "\n".join(captured.output))
        CHECKS.append({"case": "unexpected failure returns sanitized 500 and sanitized diagnostic", "passed": True})

    def test_08d_mid_migration_failure_rolls_back_schema_and_data(self):
        from src.database import migrate
        self.legacy_fixture()
        before = list(self.db.iterdump())
        with patch("src.database.generate_password_hash", side_effect=[PASSWORD_HASH, RuntimeError("controlled hash failure")]):
            with self.assertRaises(RuntimeError):
                migrate(self.db)
        self.assertEqual(list(self.db.iterdump()), before)
        self.assertFalse(self.db.in_transaction)
        CHECKS.append({"case": "mid-migration hashing failure rolls back schema, passwords, IDs and sequences", "passed": True})

    def test_08e_migration_uses_columns_instead_of_physical_order(self):
        from src.database import migrate
        self.legacy_fixture(reordered=True)
        before = {table: dict(self.db.execute(f"SELECT * FROM {table}").fetchone())
                  for table in ("produtos", "pedidos", "itens_pedido")}
        migrate(self.db)
        after = {table: dict(self.db.execute(f"SELECT * FROM {table}").fetchone())
                 for table in before}
        self.assertEqual(after, before)
        self.assertEqual(after["produtos"]["preco"], 10)
        self.assertEqual(after["produtos"]["estoque"], 5)
        CHECKS.append({"case": "migration preserves reordered columns and their numeric meanings", "passed": True})

    def test_08f_aggregate_overflow_is_refused_without_infinity_json(self):
        from src.database import initialize
        from src import create_app
        from src.services.reports import ReportService
        from src.errors import ApiError
        initialize(self.db)
        self.db.execute("INSERT INTO usuarios(id,nome,email,senha,tipo,ativo) VALUES(1,'Overflow Fixture',?,?,'admin',1)", (ADMIN[0], PASSWORD_HASH))
        for _ in range(2):
            self.db.execute("INSERT INTO pedidos(usuario_id,total,status) VALUES(1,?,'aprovado')", (1e308,))
        with self.assertRaises(ApiError) as caught:
            ReportService(self.db).sales()
        self.assertEqual(caught.exception.status, 409)
        app = create_app({"DATABASE": str(self.path), "TESTING": True})
        encoded = base64.b64encode(f"{ADMIN[0]}:{ADMIN[1]}".encode()).decode()
        with app.test_client() as client:
            result = client.get("/relatorios/vendas", headers={"Authorization": f"Basic {encoded}"})
        self.assertEqual(result.status_code, 409)
        self.assertNotIn("Infinity", result.get_data(as_text=True))
        self.assertNotIn("NaN", result.get_data(as_text=True))
        CHECKS.append({"case": "finite individual sales aggregate overflow returns 409 without nonfinite JSON", "passed": True})

    def test_09_cli_initialization_and_admin_provisioning(self):
        from src import create_app
        app = create_app({"DATABASE": str(self.path), "TESTING": True})
        runner = app.test_cli_runner()
        self.assertEqual(runner.invoke(args=["init-db"]).exit_code, 0)
        result = runner.invoke(args=["create-admin", "--nome", "Provisioned", "--email", "provisioned@example.test", "--password", PASSWORD])
        self.assertEqual(result.exit_code, 0, "create-admin CLI failed")
        self.assertNotIn(PASSWORD, result.output)
        stored = self.db.execute("SELECT senha,tipo FROM usuarios WHERE email=?", ("provisioned@example.test",)).fetchone()
        self.assertEqual(stored["tipo"], "admin")
        self.assertTrue(check_password_hash(stored["senha"], PASSWORD))
        with app.test_client() as client:
            result = client.post("/login", json={"email": "provisioned@example.test", "senha": PASSWORD})
            self.assertEqual(result.status_code, 200)
        CHECKS.append({"case": "explicit CLI initialization and administrator provisioning", "passed": True})

    def test_10_batched_order_queries_and_discount_boundaries(self):
        from src.database import initialize
        from src.models.orders import OrderModel
        from src.services.reports import ReportService
        initialize(self.db)
        self.db.execute("INSERT INTO usuarios(id,nome,email,senha,tipo,ativo) VALUES(1,'Fixture','fixture@example.test',?,'cliente',1)", (PASSWORD_HASH,))
        self.db.execute("INSERT INTO produtos(id,nome,descricao,preco,estoque,categoria) VALUES(1,'Fixture','Fixture',10,100,'geral')")
        for count in (1, 20):
            self.db.execute("DELETE FROM itens_pedido")
            self.db.execute("DELETE FROM pedidos")
            for number in range(1, count + 1):
                self.db.execute("INSERT INTO pedidos(id,usuario_id,total,status) VALUES(?,1,10,'aprovado')", (number,))
                self.db.execute("INSERT INTO itens_pedido(pedido_id,produto_id,quantidade,preco_unitario) VALUES(?,1,1,10)", (number,))
            queries = []
            self.db.set_trace_callback(lambda sql: queries.append(sql) if sql.lstrip().upper().startswith("SELECT") else None)
            try:
                rows = OrderModel(self.db).list()
            finally:
                self.db.set_trace_callback(None)
            self.assertEqual(len(rows), count)
            self.assertLessEqual(len(queries), 2)
            self.assertTrue(all(row["itens"][0]["produto_nome"] == "Fixture" for row in rows))
        self.db.execute("DELETE FROM itens_pedido")
        self.db.execute("DELETE FROM pedidos")
        self.assertEqual(ReportService(self.db).sales()["ticket_medio"], 0)
        for total, fraction in ((999.99, 0), (1000, 0), (1000.01, .02),
                                (4999.99, .02), (5000, .02), (5000.01, .05),
                                (9999.99, .05), (10000, .05), (10000.01, .10)):
            self.db.execute("DELETE FROM pedidos")
            self.db.execute("INSERT INTO pedidos(usuario_id,total,status) VALUES(1,?,'aprovado')", (total,))
            report = ReportService(self.db).sales()
            self.assertEqual(report["desconto_aplicavel"], round(total * fraction, 2))
            self.assertEqual(report["faturamento_liquido"], round(total - total * fraction, 2))
        CHECKS.append({"case": "order queries bounded at 1/20 orders; strict discount thresholds", "passed": True})


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    evidence = {
        "source": "current working tree (no git archive)",
        "command": ".venv/bin/python tests/run_validation.py",
        "python": sys.version.split()[0], "sqlite": sqlite3.sqlite_version,
        "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "passed": result.wasSuccessful(), "baseline_scenarios": 39,
        "http_checks": len([item for item in CHECKS if "observed_status" in item]),
        "operations_exercised": len(OPERATIONS & EXPECTED_OPERATIONS),
        "operations_expected": len(EXPECTED_OPERATIONS),
        "uncovered_operations": [list(item) for item in sorted(EXPECTED_OPERATIONS - OPERATIONS)],
        "checks": CHECKS, "boot_log": BOOT_LOGS,
    }
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    sys.exit(0 if result.wasSuccessful() else 1)
