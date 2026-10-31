#!/usr/bin/env python3
"""Exercise current sources through HTTP, with isolated SQLite and scrubbed evidence.

Only the historical scenario definitions are reused. This runner never imports
the legacy Baseline executor, checks out a commit, or runs git archive.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, ProxyHandler, build_opener


PROJECT = Path(__file__).resolve().parents[1]
REPOSITORY = PROJECT.parent
sys.path.insert(0, str(PROJECT))
PASSWORD = "validation-disposable-password"
ADMIN_EMAIL = "validation.admin@example.test"
SENSITIVE = re.compile(r"password|senha|secret|token|authorization|hash", re.I)
NO_BODY = object()


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def scrub(value):
    if isinstance(value, dict):
        return {str(k): "[MASCARADO]" if SENSITIVE.search(str(k)) and k != "source_hashes" else scrub(v)
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [scrub(v) for v in value]
    return value


def exposes_secret(value):
    if isinstance(value, dict):
        return any(str(k).lower() in {"password", "password_hash", "senha", "secret_key"}
                   or exposes_secret(v) for k, v in value.items())
    return isinstance(value, list) and any(exposes_secret(v) for v in value)


def source_hashes():
    return {str(p.relative_to(PROJECT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(PROJECT.rglob("*.py"))
            if not any(x in p.parts for x in (".venv", ".agents", "__pycache__"))}


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


class Validation:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="task-manager-validation-")
        self.db_path = Path(self.temp.name) / "validation.db"
        self.uri = f"sqlite:///{self.db_path}"
        self.results = []
        self.routes = []
        self.notes = []
        self.baseline_limitations = []
        self.process = None
        self.log_file = None
        self.server_log = ""
        self.admin_token = None
        self.before_sources = source_hashes()
        self.local_database = PROJECT / "instance/tasks.db"
        self.before_local_database = file_hash(self.local_database)
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.opener = build_opener(ProxyHandler({}))
        self.query_measurements = []
        self.actual_inventory = []

    def inventory(self, routes):
        self.routes = routes

    def add_finding(self, text):
        self.notes.append(text)

    def add_limitation(self, text):
        self.baseline_limitations.append(text)

    def query(self, statement, params=()):
        with sqlite3.connect(self.db_path, timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute(statement, params)]

    def execute(self, statement, params=()):
        with sqlite3.connect(self.db_path, timeout=10) as connection:
            connection.execute(statement, params)

    def state(self):
        """Full-row fingerprint detects updates as well as row-count changes."""
        with sqlite3.connect(self.db_path, timeout=10) as connection:
            names = [r[0] for r in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            state = {name: connection.execute(f'SELECT * FROM "{name}" ORDER BY rowid').fetchall()
                     for name in names}
        return hashlib.sha256(json.dumps(state, default=str, sort_keys=True).encode()).hexdigest()

    def counts(self):
        with sqlite3.connect(self.db_path, timeout=10) as connection:
            names = [r[0] for r in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            return {name: connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for name in names}

    def fixture(self, app, count=10):
        from database import db
        from models.user import User
        from models.task import Task
        from models.category import Category

        with app.app_context():
            db.create_all()
            users = []
            for name, email, role in [("Validation Admin", ADMIN_EMAIL, "admin"),
                                      ("Validation User", "validation.user@example.test", "user"),
                                      ("Validation Manager", "validation.manager@example.test", "manager")]:
                user = User(name=name, email=email, role=role, active=True)
                user.set_password(PASSWORD)
                users.append(user)
                db.session.add(user)
            categories = [Category(name=name, description="Fixture", color="#123456")
                          for name in ("Backend", "Frontend", "DevOps", "Bug")]
            db.session.add_all(categories)
            db.session.flush()
            owners = [0, 1, 2, 0, 0, 1, 2, 1, 2, 0]
            priorities = [1, 2, 2, 1, 3, 2, 4, 3, 4, 3]
            statuses = ["pending", "in_progress", "done", "pending", "pending", "pending", "cancelled", "in_progress", "pending", "pending"]
            for index in range(count):
                due = utc_now() - timedelta(days=3) if index in (0, 3) else None
                db.session.add(Task(title=f"Fixture task {index+1}", description="Regression fixture",
                                    status=statuses[index % 10], priority=priorities[index % 10],
                                    user_id=users[owners[index % 10]].id,
                                    category_id=categories[index % 4].id, due_date=due))
            db.session.commit()

    def start_flask(self, seed=False):
        from app import create_app

        # A factory/import is explicitly allowed now; only disposable DB is used.
        app = create_app({"SQLALCHEMY_DATABASE_URI": self.uri, "TESTING": False})
        self.actual_inventory = sorted((method, rule.rule) for rule in app.url_map.iter_rules()
                                       if rule.endpoint != "static"
                                       for method in rule.methods - {"HEAD", "OPTIONS"})
        self.fixture(app)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        log_path = Path(self.temp.name) / "server.log"
        self.log_file = log_path.open("w+")
        env = {**os.environ, "DATABASE_URL": self.uri, "HOST": "127.0.0.1", "PORT": str(self.port),
               "FLASK_DEBUG": "0", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"}
        self.process = subprocess.Popen([sys.executable, "-B", "app.py"], cwd=PROJECT, env=env,
                                        stdout=self.log_file, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"Current app.py failed boot: exit {self.process.returncode}")
            try:
                with self.opener.open(f"http://127.0.0.1:{self.port}/health", timeout=0.5) as response:
                    if response.code == 200:
                        break
            except (URLError, OSError):
                time.sleep(0.05)
        else:
            raise RuntimeError("Current app.py readiness timeout")
        result = self.case("Autenticar administrador de teste", "POST", "/login",
                           {"email": ADMIN_EMAIL, "password": PASSWORD}, token=None)
        self.admin_token = result["body"].get("token")
        if not self.admin_token:
            raise RuntimeError("Administrator fixture cannot authenticate")

    def case(self, name, method, path, payload=None, expected=200, expectation="", route=None,
             *, token=NO_BODY, unchanged=False, raw=NO_BODY, content_type="application/json"):
        # Baseline security corrections: retain protected successes using admin,
        # but preserve anonymous security cases as actual anonymous requests.
        anonymous_detail = name == "Detalhe do usuário seed sem autenticação"
        if anonymous_detail:
            token, expected = None, [401, 403]
        if name == "Cliente promove usuário a admin sem autorização":
            token = None
        if token is NO_BODY:
            token = None if method == "POST" and path in ("/users", "/login") else self.admin_token
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if raw is not NO_BODY:
            data = raw.encode() if isinstance(raw, str) else raw
            headers["Content-Type"] = content_type
        elif payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = content_type
        else:
            data = None
        before_state, before_counts = self.state(), self.counts()
        request = Request(f"http://127.0.0.1:{self.port}{path}", method=method, data=data, headers=headers)
        result = {"id": f"V3-{len(self.results)+1:03d}", "name": name, "method": method,
                  "path": path, "route": route or path.split("?", 1)[0], "request": payload,
                  "authenticated": bool(token), "expected_status": expected, "expectation": expectation,
                  "checks": [], "notes": [], "db_before": before_counts}
        try:
            try:
                response = self.opener.open(request, timeout=10)
            except HTTPError as error:
                response = error
            with response:
                result["status"] = response.code
                result["content_type"] = response.headers.get("Content-Type", "")
                body = response.read().decode("utf-8", errors="replace")
            try:
                result["body"] = json.loads(body)
            except json.JSONDecodeError:
                result["body"] = body
        except (URLError, OSError, TimeoutError) as error:
            result.update(status=None, body=f"Transport failure: {type(error).__name__}")
        result["db_after"] = self.counts()
        self.results.append(result)
        allowed = expected if isinstance(expected, (list, tuple)) else [expected]
        self.check(result, "HTTP esperado", result["status"] in allowed, True)
        self.check(result, "Resposta JSON", "application/json" in result.get("content_type", ""), True)
        self.check(result, "Resposta omite senha e hash", exposes_secret(result["body"]), False)
        if unchanged:
            self.check(result, "Todas as linhas preservadas", self.state() == before_state, True)
        return result

    def check(self, result, name, actual, expected):
        result["checks"].append({"name": name, "actual": actual, "expected": expected, "ok": actual == expected})

    def note(self, result, text):
        result["notes"].append(text)

    def invariant(self, name, actual, expected=True):
        result = {"id": f"V3-{len(self.results)+1:03d}", "name": name, "checks": [], "notes": []}
        self.results.append(result)
        self.check(result, name, actual, expected)
        return result

    def login(self, email, password=PASSWORD):
        result = self.case("Login de fixture", "POST", "/login", {"email": email, "password": password}, token=None)
        token = result["body"].get("token") if isinstance(result["body"], dict) else None
        if not token:
            raise RuntimeError("Fixture login did not return token")
        return token

    def extra_cases(self):
        admin = self.admin_token
        user = self.login("validation.user@example.test")
        manager = self.login("validation.manager@example.test")
        self.invariant("Cadastro administrativo rejeitado não deixou conta",
                       self.query("SELECT COUNT(*) n FROM users WHERE email='baseline.admin@example.test'")[0]["n"], 0)
        for method, path, data in [("GET", "/tasks", None), ("GET", "/users", None),
                                   ("GET", "/categories", None), ("GET", "/reports/summary", None),
                                   ("DELETE", "/users/2", None), ("POST", "/categories", {"name": "Denied"})]:
            self.case("Operação protegida sem credencial", method, path, data, expected=401,
                      token=None, unchanged=True,
                      route="/users/<int:user_id>" if path == "/users/2" else None)
        for token in ("invalid-token", "fake-jwt-token-1", admin + "tampered"):
            self.case("Token inválido rejeitado", "GET", "/tasks", expected=401, token=token, unchanged=True)
        for token in (user, manager):
            for method, path, data in [("GET", "/users", None), ("GET", "/reports/summary", None),
                                       ("POST", "/categories", {"name": "Denied"}),
                                       ("PUT", "/categories/1", {"name": "Denied"}),
                                       ("DELETE", "/categories/1", None), ("DELETE", "/users/1", None),
                                       ("PUT", "/users/2", {"role": "admin"}),
                                       ("PUT", "/users/2", {"active": False})]:
                self.case("Usuário/manager sem privilégio administrativo", method, path, data,
                          expected=403, token=token, unchanged=True)
        for path in ("/users/1", "/users/1/tasks", "/reports/user/1", "/tasks/1"):
            self.case("Leitura de recurso alheio negada", "GET", path, expected=403, token=user, unchanged=True)
        for method, data in [("PUT", {"title": "Forbidden update"}), ("DELETE", None)]:
            self.case("Mutação de task alheia negada", method, "/tasks/1", data,
                      expected=403, token=user, unchanged=True)
        for payload in ({"title": "Forbidden owner", "user_id": 1}, {"title": "Unassigned", "user_id": None}):
            self.case("Atribuição de task exige autorização", "POST", "/tasks", payload,
                      expected=403, token=user, unchanged=True)
        for path in ("/tasks", "/tasks/search"):
            result = self.case("Listagem restrita ao titular", "GET", path, token=user)
            self.check(result, "Todas as tasks pertencem ao titular", all(t["user_id"] == 2 for t in result["body"]), True)
        result = self.case("Estatísticas restritas ao titular", "GET", "/tasks/stats", token=user)
        count = self.query("SELECT COUNT(*) n FROM tasks WHERE user_id=2")[0]["n"]
        self.check(result, "Total próprio", result["body"].get("total"), count)
        self.case("Filtro de usuário alheio negado", "GET", "/tasks/search?user_id=1", token=user,
                  expected=403, unchanged=True)
        self.case("Perfil próprio autorizado", "GET", "/users/2", token=user)
        self.case("Tasks próprias autorizadas", "GET", "/users/2/tasks", token=user)
        self.case("Relatório próprio autorizado", "GET", "/reports/user/2", token=user)
        self.case("Categorias autenticadas", "GET", "/categories", token=user)
        own = self.case("Criação atribui titular automaticamente", "POST", "/tasks",
                        {"title": "Own task", "tags": ["regression"]}, expected=201, token=user)
        own_id = own["body"].get("id")
        self.check(own, "Atribuída ao titular", own["body"].get("user_id"), 2)
        self.case("Titular atualiza task", "PUT", f"/tasks/{own_id}", {"priority": 5}, token=user)
        self.case("Titular remove task", "DELETE", f"/tasks/{own_id}", token=user)

        # Type and boundary validation must leave every persisted field unchanged.
        invalid_tasks = [{"title": 123}, {"title": True}, {"title": []}, {"title": "ab"},
                         {"title": "x" * 201}, {"title": "   "},
                         *({"title": "Invalid type", "priority": v} for v in (True, None, "alta", 0, 6, 1.5)),
                         {"title": "Invalid id", "user_id": True},
                         {"title": "Invalid id", "category_id": 0},
                         {"title": "Invalid tags", "tags": [123]},
                         {"title": "Invalid tags", "tags": {}},
                         {"title": "Invalid date", "due_date": 123},
                         {"title": "Invalid description", "description": []}]
        for payload in invalid_tasks:
            self.case("Task inválida rejeitada sem alteração", "POST", "/tasks", payload,
                      expected=400, unchanged=True)
        for payload in ({"title": 123}, {"priority": True}, {"tags": [False]},
                        {"title": "Should rollback", "status": "invalid"}):
            self.case("Update inválido sem alteração parcial", "PUT", "/tasks/1", payload,
                      expected=400, unchanged=True)
        for path in ("/tasks/search?priority=0", "/tasks/search?priority=1.5", "/tasks/search?user_id=-1",
                     "/tasks/search?status=invalid"):
            self.case("Filtro inválido rejeitado", "GET", path, expected=400, unchanged=True)
        huge = 2 ** 80
        for payload in ({"title": "Huge user", "user_id": huge},
                        {"title": "Huge category", "category_id": huge}):
            self.case("ID JSON fora do limite SQLite", "POST", "/tasks", payload,
                      expected=400, unchanged=True)
        self.case("Update com ID fora do limite SQLite", "PUT", "/tasks/1", {"category_id": huge},
                  expected=400, unchanged=True)
        self.case("Filtro com ID fora do limite SQLite", "GET", f"/tasks/search?user_id={huge}",
                  expected=400, unchanged=True)
        for method, path, payload in (("GET", f"/tasks/{huge}", None),
                                      ("GET", f"/users/{huge}", None),
                                      ("GET", f"/users/{huge}/tasks", None),
                                      ("GET", f"/reports/user/{huge}", None),
                                      ("PUT", f"/categories/{huge}", {"name": "Huge"}),
                                      ("DELETE", f"/categories/{huge}", None)):
            self.case("ID de rota fora do limite SQLite", method, path, payload,
                      expected=400, unchanged=True)
        for method, path in (("POST", "/tasks"), ("PUT", "/tasks/1"), ("POST", "/users"),
                             ("PUT", "/users/2"), ("POST", "/login"), ("POST", "/categories"),
                             ("PUT", "/categories/1")):
            for raw in ("null", "[]", "[1]", '"text"', "{broken"):
                self.case("JSON inválido rejeitado", method, path, expected=400,
                          raw=raw, unchanged=True)
        for payload in ({"name": "Invalid", "email": 12, "password": PASSWORD},
                        {"name": "Invalid", "email": "typed@example.test", "password": 1234},
                        {"name": [], "email": "typed@example.test", "password": PASSWORD}):
            self.case("Tipos de cadastro inválidos", "POST", "/users", payload, expected=400, unchanged=True)
        for payload in ({"name": ""}, {"active": "false"}, {"password": 123}, {"email": []}):
            self.case("Tipos de perfil inválidos", "PUT", "/users/2", payload, expected=400, unchanged=True)
        for payload in ({"name": []}, {"name": "Invalid", "color": "#zzzzzz"},
                        {"name": "Invalid", "color": 123}, {"name": " "}):
            self.case("Categoria inválida rejeitada", "POST", "/categories", payload, expected=400, unchanged=True)

        # Category deletion preserves linked tasks and explicitly nulls relation.
        category = self.case("Categoria vinculada de teste", "POST", "/categories", {"name": "Linked fixture"}, expected=201)
        cat_id = category["body"]["id"]
        task = self.case("Task vinculada à categoria", "POST", "/tasks",
                         {"title": "Linked category task", "user_id": 2, "category_id": cat_id}, expected=201)
        task_id = task["body"]["id"]
        result = self.case("Excluir categoria mantém tasks", "DELETE", f"/categories/{cat_id}")
        self.check(result, "Task preservada e categoria nula", self.query("SELECT category_id FROM tasks WHERE id=?", (task_id,)), [{"category_id": None}])
        self.case("Limpar task vinculada", "DELETE", f"/tasks/{task_id}")

        # Single-transaction failure checks use actual SQLite constraints/triggers.
        self.execute("CREATE TRIGGER fail_task_update BEFORE UPDATE ON tasks WHEN NEW.title='Injected failure' BEGIN INSERT INTO synthetic_sensitive_marker VALUES(1); END")
        self.case("Falha de banco retorna JSON genérico e rollback", "PUT", "/tasks/1",
                  {"title": "Injected failure", "priority": 4}, expected=500, unchanged=True)
        self.execute("DROP TRIGGER fail_task_update")
        self.case("Aplicação atende após rollback", "GET", "/tasks/1")
        victim = self.case("Usuário para rollback de cascade", "POST", "/users",
                           {"name": "Cascade fixture", "email": "cascade@example.test", "password": PASSWORD}, expected=201)
        victim_id = victim["body"]["id"]
        self.case("Task para rollback de cascade", "POST", "/tasks", {"title": "Cascade fixture task", "user_id": victim_id}, expected=201)
        self.execute(f"CREATE TRIGGER fail_user_delete BEFORE DELETE ON users WHEN OLD.id={int(victim_id)} BEGIN INSERT INTO synthetic_sensitive_marker VALUES(1); END")
        self.case("Falha ao excluir usuário preserva tarefas", "DELETE", f"/users/{victim_id}", expected=500, unchanged=True)
        self.execute("DROP TRIGGER fail_user_delete")
        self.case("Exclusão cascade após remover falha", "DELETE", f"/users/{victim_id}")

        # Sessions: digest-only persistence, explicit expiration and live user state.
        columns = {row["name"] for row in self.query("PRAGMA table_info(auth_sessions)")}
        digest_column = next((name for name in ("token_hash", "token_digest", "digest") if name in columns), None)
        if not digest_column:
            raise RuntimeError("Cannot identify session digest column")
        self.invariant("Sessões persistem somente digest do token",
                       bool(self.query(f"SELECT 1 FROM auth_sessions WHERE {digest_column}=?", (hashlib.sha256(user.encode()).hexdigest(),))))
        self.invariant("Token bruto ausente do banco", user.encode() not in self.db_path.read_bytes())
        expired = self.login("validation.manager@example.test")
        self.execute(f"UPDATE auth_sessions SET expires_at='2000-01-01 00:00:00' WHERE {digest_column}=?", (hashlib.sha256(expired.encode()).hexdigest(),))
        self.case("Sessão expirada rejeitada", "GET", "/tasks", token=expired, expected=401, unchanged=True)
        self.case("Inativação administrativa", "PUT", "/users/2", {"active": False})
        self.invariant("Inativação persistida", self.query("SELECT active FROM users WHERE id=2"), [{"active": 0}])
        self.case("Sessão de usuário inativo negada", "GET", "/tasks", token=user, expected=[401, 403], unchanged=True)
        self.case("Reativação administrativa", "PUT", "/users/2", {"active": True})
        user = self.login("validation.user@example.test")
        new_password = "changed-disposable-password"
        self.case("Titular altera senha", "PUT", "/users/2", {"password": new_password}, token=user)
        self.case("Troca de senha revoga sessão", "GET", "/tasks", token=user, expected=401, unchanged=True)
        self.case("Senha anterior deixa de autenticar", "POST", "/login",
                  {"email": "validation.user@example.test", "password": PASSWORD}, expected=401, unchanged=True)
        self.login("validation.user@example.test", new_password)

        # Legacy hashes are replaced only after successful, active authentication.
        legacy_password = "legacy-disposable-password"
        md5 = hashlib.md5(legacy_password.encode()).hexdigest()
        self.execute("INSERT INTO users(name,email,password,role,active,created_at) VALUES(?,?,?,?,?,?)",
                     ("Legacy fixture", "legacy@example.test", md5, "user", 1, str(utc_now())))
        legacy_id = self.query("SELECT id FROM users WHERE email='legacy@example.test'")[0]["id"]
        self.case("Senha legada incorreta não migra", "POST", "/login",
                  {"email": "legacy@example.test", "password": "wrong-fixture"}, expected=401, unchanged=True)
        self.execute("UPDATE users SET active=0 WHERE id=?", (legacy_id,))
        self.case("Conta legada inativa não migra", "POST", "/login",
                  {"email": "legacy@example.test", "password": legacy_password}, expected=403, unchanged=True)
        self.execute("UPDATE users SET active=1 WHERE id=?", (legacy_id,))
        self.login("legacy@example.test", legacy_password)
        stored = self.query("SELECT password FROM users WHERE id=?", (legacy_id,))[0]["password"]
        from werkzeug.security import check_password_hash
        self.invariant("MD5 migrou após senha correta", stored != md5 and check_password_hash(stored, legacy_password))
        self.invariant("Contas com mesma senha recebem salts distintos",
                       len({r["password"] for r in self.query("SELECT password FROM users WHERE id IN (1,3)")}) == 2)
        self.case("Login após migração mantém conta", "POST", "/login",
                  {"email": "legacy@example.test", "password": legacy_password})
        long_email = "legacy." + "x" * 145 + "@example.test"
        long_password = "L" * 1025
        legacy_long_md5 = hashlib.md5(long_password.encode()).hexdigest()
        self.execute("INSERT INTO users(name,email,password,role,active,created_at) VALUES(?,?,?,?,?,?)",
                     ("Long legacy fixture", long_email, legacy_long_md5, "user", 1, str(utc_now())))
        self.case("Senha longa legada incorreta não migra", "POST", "/login",
                  {"email": long_email, "password": "X" + long_password[1:]}, expected=401, unchanged=True)
        migrated_long = self.case("Credenciais longas legadas continuam válidas", "POST", "/login",
                                  {"email": long_email, "password": long_password})
        stored_long = self.query("SELECT password FROM users WHERE email=?", (long_email,))[0]["password"]
        self.check(migrated_long, "MD5 longo migrou após login correto",
                   stored_long != legacy_long_md5 and check_password_hash(stored_long, long_password), True)
        self.case("Cadastro novo mantém limite de email", "POST", "/users",
                  {"name": "Long signup", "email": "new." + "x" * 145 + "@example.test", "password": PASSWORD},
                  expected=400, unchanged=True)
        self.case("Cadastro novo mantém limite de senha", "POST", "/users",
                  {"name": "Long signup", "email": "new.long@example.test", "password": long_password},
                  expected=400, unchanged=True)
        self.case("Admin promove papel explicitamente", "PUT", "/users/3", {"role": "admin"})
        promoted = self.login("validation.manager@example.test")
        self.case("Papel administrativo atualizado no servidor", "GET", "/users", token=promoted)
        self.case("Admin revoga papel explicitamente", "PUT", "/users/3", {"role": "manager"})
        self.case("Sessão lê papel atual do servidor", "GET", "/users", token=promoted, expected=403, unchanged=True)

    def unicode_cases(self):
        """C-01: reject lone JSON surrogates before hashing or SQL writes.

        The ordinary HTTP helper JSON-escapes payloads, so these cases reach the
        actual parser rather than failing in the test client's UTF-8 encoder.
        A valid non-BMP character is also sent as an explicit JSON surrogate pair.
        """
        from werkzeug.security import check_password_hash

        legacy_email = "unicode.legacy@example.test"
        legacy_password = "unicode-legacy-disposable-password"
        self.execute("INSERT INTO users(name,email,password,role,active,created_at) VALUES(?,?,?,?,?,?)",
                     ("Unicode legacy fixture", legacy_email,
                      hashlib.md5(legacy_password.encode()).hexdigest(), "user", 1, str(utc_now())))
        legacy_id = self.query("SELECT id FROM users WHERE email=?", (legacy_email,))[0]["id"]

        for surrogate, label in (("\ud800", "high"), ("\udfff", "low")):
            bad_text = "Invalid " + surrogate
            signup = {"name": "Unicode invalid fixture", "email": "unicode.invalid@example.test",
                      "password": PASSWORD}
            for field in ("name", "email", "password"):
                self.case(f"C-01 cadastro rejeita surrogate {label} em {field}", "POST", "/users",
                          {**signup, field: bad_text}, expected=400, unchanged=True)
                self.case(f"C-01 perfil rejeita surrogate {label} em {field}", "PUT", "/users/2",
                          {"name": "Should remain unchanged", field: bad_text}, expected=400, unchanged=True)
            for email, credential_kind in ((ADMIN_EMAIL, "hash atual"), (legacy_email, "MD5 legado")):
                self.case(f"C-01 login {credential_kind} rejeita senha surrogate {label}",
                          "POST", "/login", {"email": email, "password": bad_text},
                          expected=400, unchanged=True)
            self.case(f"C-01 login rejeita email surrogate {label}", "POST", "/login",
                      {"email": bad_text, "password": PASSWORD}, expected=400, unchanged=True)
            for field, value in (("title", bad_text), ("description", bad_text),
                                 ("tags", bad_text), ("tags", ["Valid", bad_text])):
                tag_kind = " lista" if isinstance(value, list) else ""
                self.case(f"C-01 task rejeita surrogate {label} em {field}{tag_kind}",
                          "POST", "/tasks", {"title": "Unicode invalid task", field: value},
                          expected=400, unchanged=True)
                self.case(f"C-01 update de task rejeita surrogate {label} em {field}{tag_kind}",
                          "PUT", "/tasks/1", {"title": "Should remain unchanged", field: value},
                          expected=400, unchanged=True)
            for field in ("name", "description"):
                self.case(f"C-01 categoria rejeita surrogate {label} em {field}",
                          "POST", "/categories", {"name": "Unicode invalid category", field: bad_text},
                          expected=400, unchanged=True)
                self.case(f"C-01 update de categoria rejeita surrogate {label} em {field}",
                          "PUT", "/categories/1", {"name": "Should remain unchanged", field: bad_text},
                          expected=400, unchanged=True)

        # Check real UTF-8 text after JSON decoding, persisted values and login;
        # normal accents, combining marks and surrogate pairs must not be rejected.
        email = "unicode.valid@example.test"
        password = "Senha válida 😀"
        name = "José 😀"
        signup = {"name": name, "email": email, "password": password}
        raw_signup = json.dumps(signup, ensure_ascii=True)
        created = self.case("C-01 cadastro aceita acento e par surrogate válido", "POST", "/users",
                            raw=raw_signup, expected=201)
        user_id = created["body"]["id"]
        self.check(created, "Nome Unicode público preservado", created["body"].get("name"), name)
        self.check(created, "Nome Unicode persistido sem alteração",
                   self.query("SELECT name FROM users WHERE id=?", (user_id,)), [{"name": name}])
        stored = self.query("SELECT password FROM users WHERE id=?", (user_id,))[0]["password"]
        self.check(created, "Senha Unicode recebe hash verificável", check_password_hash(stored, password), True)
        logged_in = self.case("C-01 login aceita senha com emoji", "POST", "/login",
                              {"email": email, "password": password})
        user_token = logged_in["body"]["token"]
        self.check(logged_in, "Login mantém nome Unicode", logged_in["body"]["user"].get("name"), name)

        category_values = {"name": "Revisão 🚀", "description": "Descrição de ação 🧪"}
        category = self.case("C-01 categoria aceita Unicode válido", "POST", "/categories",
                             category_values, expected=201)
        category_id = category["body"]["id"]
        self.check(category, "Categoria Unicode persistida",
                   self.query("SELECT name,description FROM categories WHERE id=?", (category_id,)),
                   [category_values])
        task_values = {"title": "Revisão 🚀", "description": "Descrição de ação e café 🧪",
                       "tags": ["ação", "🚀"], "category_id": category_id}
        task = self.case("C-01 task aceita acento e emoji", "POST", "/tasks", task_values,
                         expected=201, token=user_token)
        task_id = task["body"]["id"]
        self.check(task, "Texto e tags Unicode persistidos",
                   self.query("SELECT title,description,tags FROM tasks WHERE id=?", (task_id,)),
                   [{"title": task_values["title"], "description": task_values["description"],
                     "tags": "ação,🚀"}])
        detail = self.case("C-01 leitura mantém Unicode e tags", "GET", f"/tasks/{task_id}", token=user_token)
        for field in ("title", "description", "tags"):
            self.check(detail, f"Campo {field} preservado", detail["body"].get(field), task_values[field])
        search = self.case("C-01 busca Unicode usa HTTP percent-encoded", "GET",
                           "/tasks/search?" + urlencode({"q": "🚀"}), token=user_token,
                           unchanged=True, route="/tasks/search")
        self.check(search, "Busca retorna a task com emoji", [row["id"] for row in search["body"]], [task_id])

        updated_task = {"title": "Tarefa atualizada 🧪", "description": "Revisão com café",
                        "tags": "revisão,🧪"}
        edited = self.case("C-01 edição de task aceita Unicode válido", "PUT", f"/tasks/{task_id}",
                           updated_task, token=user_token)
        self.check(edited, "Unicode atualizado no SQLite",
                   self.query("SELECT title,description,tags FROM tasks WHERE id=?", (task_id,)), [updated_task])
        updated_category = {"name": "Categoria atualizada 🧪", "description": "Descrição revisada"}
        edited_category = self.case("C-01 edição de categoria aceita Unicode válido", "PUT",
                                    f"/categories/{category_id}", updated_category)
        self.check(edited_category, "Categoria atualizada no SQLite",
                   self.query("SELECT name,description FROM categories WHERE id=?", (category_id,)),
                   [updated_category])

        updated_name = "Jose\u0301 atualizado 🧪"
        updated_password = "Outra senha válida 🧪"
        edited_user = self.case("C-01 edição de perfil aceita Unicode sem normalizar", "PUT",
                                f"/users/{user_id}", {"name": updated_name, "password": updated_password},
                                token=user_token)
        self.check(edited_user, "Combining mark preservado na resposta", edited_user["body"].get("name"), updated_name)
        self.check(edited_user, "Combining mark preservado no SQLite",
                   self.query("SELECT name FROM users WHERE id=?", (user_id,)), [{"name": updated_name}])
        self.case("C-01 troca de senha Unicode revoga sessão", "GET", "/tasks", token=user_token,
                  expected=401, unchanged=True)
        self.case("C-01 senha Unicode atualizada autentica", "POST", "/login",
                  {"email": email, "password": updated_password})
        self.case("C-01 remover fixture Unicode e tarefas", "DELETE", f"/users/{user_id}")
        self.case("C-01 remover categoria Unicode", "DELETE", f"/categories/{category_id}")
        self.case("C-01 remover fixture MD5 Unicode", "DELETE", f"/users/{legacy_id}")

    def report_and_boundary_cases(self):
        empty_email = "empty.report@example.test"
        created = self.case("Usuário sem tarefas para agregações", "POST", "/users",
                            {"name": "Empty Report", "email": empty_email, "password": PASSWORD}, expected=201)
        empty_id = created["body"]["id"]
        empty_token = self.login(empty_email)
        empty_category = self.case("Categoria sem tarefas para agregações", "POST", "/categories",
                                   {"name": "Empty category"}, expected=201)
        empty_category_id = empty_category["body"]["id"]
        users = self.case("Listagem preserva usuário sem tarefas", "GET", "/users")
        self.check(users, "Contagem zero do usuário", next(u["task_count"] for u in users["body"] if u["id"] == empty_id), 0)
        categories = self.case("Listagem preserva categoria sem tarefas", "GET", "/categories")
        self.check(categories, "Contagem zero da categoria", next(c["task_count"] for c in categories["body"] if c["id"] == empty_category_id), 0)
        stats = self.case("Estatísticas vazias sem divisão por zero", "GET", "/tasks/stats", token=empty_token)
        self.check(stats, "Todos os totais e taxa são zero", stats["body"],
                   {"total": 0, "pending": 0, "in_progress": 0, "done": 0, "cancelled": 0,
                    "overdue": 0, "completion_rate": 0})
        report = self.case("Relatório individual vazio", "GET", f"/reports/user/{empty_id}", token=empty_token)
        self.check(report, "Estatísticas vazias", report["body"].get("statistics"),
                   {"total_tasks": 0, "pending": 0, "in_progress": 0, "done": 0, "cancelled": 0,
                    "overdue": 0, "high_priority": 0, "completion_rate": 0})
        summary = self.case("Produtividade inclui usuário sem tarefas", "GET", "/reports/summary")
        self.check(summary, "Produtividade com denominador zero",
                   next(u for u in summary["body"]["user_productivity"] if u["user_id"] == empty_id),
                   {"user_id": empty_id, "user_name": "Empty Report", "total_tasks": 0,
                    "completed_tasks": 0, "completion_rate": 0})

        # Lower and upper boundaries remain valid, including priority ordering.
        boundary_ids = []
        for title, priority in (("abc", 1), ("x" * 200, 5)):
            result = self.case("Limites válidos de título e prioridade", "POST", "/tasks",
                               {"title": title, "priority": priority, "user_id": empty_id}, expected=201)
            boundary_ids.append(result["body"]["id"])
            self.check(result, "Limites preservados", (len(result["body"].get("title", "")), result["body"].get("priority")), (len(title), priority))
        for identifier in boundary_ids:
            self.case("Limpar tarefa de limite", "DELETE", f"/tasks/{identifier}")
        self.case("JSON com Content-Type incorreto", "POST", "/tasks", expected=400,
                  raw='{"title":"Wrong media type"}', content_type="text/plain", unchanged=True)

        # Five controlled rows distinguish past/future dates and terminal states.
        now = utc_now()
        old = now - timedelta(days=30)
        recent = now - timedelta(days=2)
        past_due = now - timedelta(days=4)
        future_due = now + timedelta(days=4)
        fixtures = [("pending", 1, past_due, old, old),
                    ("pending", 2, future_due, recent, recent),
                    ("done", 3, past_due, old, recent),
                    ("cancelled", 4, past_due, recent, recent),
                    ("in_progress", 5, None, recent, old)]
        controlled_ids = []
        with sqlite3.connect(self.db_path) as connection:
            for index, (status, priority, due, created_at, updated_at) in enumerate(fixtures):
                cursor = connection.execute(
                    "INSERT INTO tasks(title,description,status,priority,user_id,category_id,due_date,created_at,updated_at,tags) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (f"Controlled report task {index}", "Controlled dates", status, priority,
                     empty_id, empty_category_id, str(due) if due else None,
                     str(created_at), str(updated_at), None))
                controlled_ids.append(cursor.lastrowid)
        stats = self.case("Estatísticas com datas e estados controlados", "GET", "/tasks/stats", token=empty_token)
        self.check(stats, "Concluídas/canceladas excluídas do atraso", stats["body"],
                   {"total": 5, "pending": 2, "in_progress": 1, "done": 1, "cancelled": 1,
                    "overdue": 1, "completion_rate": 20.0})
        report = self.case("Relatório individual com datas controladas", "GET", f"/reports/user/{empty_id}", token=empty_token)
        self.check(report, "Prioridades e taxa individual", report["body"].get("statistics"),
                   {"total_tasks": 5, "pending": 2, "in_progress": 1, "done": 1, "cancelled": 1,
                    "overdue": 1, "high_priority": 2, "completion_rate": 20.0})
        listed = self.case("Lista aplica mesma regra de atraso", "GET", "/tasks", token=empty_token)
        self.check(listed, "Apenas pendente vencida marcada", sorted(t["id"] for t in listed["body"] if t.get("overdue")), [controlled_ids[0]])
        summary = self.case("Relatório geral com janela UTC controlada", "GET", "/reports/summary")
        body = summary["body"]
        self.check(summary, "Totais gerais coincidem com SQLite", body.get("overview"),
                   {"total_tasks": self.query("SELECT COUNT(*) n FROM tasks")[0]["n"],
                    "total_users": self.query("SELECT COUNT(*) n FROM users")[0]["n"],
                    "total_categories": self.query("SELECT COUNT(*) n FROM categories")[0]["n"]})
        expected_status = {status: self.query("SELECT COUNT(*) n FROM tasks WHERE status=?", (status,))[0]["n"]
                           for status in ("pending", "in_progress", "done", "cancelled")}
        self.check(summary, "Contagens por status", body.get("tasks_by_status"), expected_status)
        expected_priority = {name: self.query("SELECT COUNT(*) n FROM tasks WHERE priority=?", (priority,))[0]["n"]
                             for priority, name in enumerate(("critical", "high", "medium", "low", "minimal"), 1)}
        self.check(summary, "Contagens por prioridade", body.get("tasks_by_priority"), expected_priority)
        since = str(now - timedelta(days=7))
        self.check(summary, "Janela de sete dias distingue criação e conclusão", body.get("recent_activity"),
                   {"tasks_created_last_7_days": self.query("SELECT COUNT(*) n FROM tasks WHERE created_at>=?", (since,))[0]["n"],
                    "tasks_completed_last_7_days": self.query("SELECT COUNT(*) n FROM tasks WHERE status='done' AND updated_at>=?", (since,))[0]["n"]})
        overdue = self.query("SELECT id FROM tasks WHERE due_date<? AND status NOT IN ('done','cancelled')", (str(now),))
        self.check(summary, "Contagem de atrasos", body.get("overdue", {}).get("count"), len(overdue))
        self.check(summary, "Lista dos atrasos coincide com SQLite", sorted(t["id"] for t in body.get("overdue", {}).get("tasks", [])), sorted(t["id"] for t in overdue))
        self.check(summary, "Produtividade individual agregada",
                   next(u for u in body["user_productivity"] if u["user_id"] == empty_id),
                   {"user_id": empty_id, "user_name": "Empty Report", "total_tasks": 5,
                    "completed_tasks": 1, "completion_rate": 20.0})
        generated = datetime.fromisoformat(body["generated_at"])
        self.check(summary, "generated_at usa UTC atual", abs((generated - utc_now()).total_seconds()) < 60, True)

    def measure_queries(self):
        from app import create_app
        from database import db
        from models.user import User
        from models.category import Category
        from models.task import Task
        from sqlalchemy import event

        uri = f"sqlite:///{Path(self.temp.name) / 'queries.db'}"
        app = create_app({"SQLALCHEMY_DATABASE_URI": uri, "TESTING": False})
        self.fixture(app)
        client = app.test_client()
        response = client.post("/login", json={"email": ADMIN_EMAIL, "password": PASSWORD})
        token = response.get_json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        with app.app_context():
            engine = db.engine
        count = [0]
        def count_query(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                count[0] += 1
        event.listen(engine, "before_cursor_execute", count_query)
        try:
            for size in (3, 43):
                if size == 43:
                    with app.app_context():
                        for index in range(40):
                            owner = User(name=f"Scale {index}", email=f"scale{index}@example.test",
                                         password="unusable-fixture", role="user", active=True)
                            category = Category(name=f"Scale {index}", color="#123456")
                            db.session.add_all([owner, category])
                            db.session.flush()
                            for number in range(3):
                                db.session.add(Task(title=f"Scale {index} task {number}", status="pending",
                                                    priority=3, user_id=owner.id, category_id=category.id))
                        db.session.commit()
                for path in ("/tasks", "/users", "/categories", "/reports/summary"):
                    count[0] = 0
                    response = client.get(path, headers=headers)
                    self.invariant(f"Consulta em lote {path} com {size} usuários", response.status_code, 200)
                    self.query_measurements.append({"users": size, "path": path, "selects": count[0]})
            for path in ("/tasks", "/users", "/categories", "/reports/summary"):
                rows = [r for r in self.query_measurements if r["path"] == path]
                self.invariant(f"Consultas não crescem por entidade: {path}", rows[1]["selects"] <= rows[0]["selects"] + 1)
        finally:
            event.remove(engine, "before_cursor_execute", count_query)

    def stop(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self.log_file:
            self.log_file.flush()
            self.log_file.seek(0)
            self.server_log = self.log_file.read()
            self.log_file.close()

    def finish(self, output, error=None):
        self.stop()
        self.invariant("Fontes permanecem iguais durante a validação", self.before_sources == source_hashes())
        self.invariant("Banco local permanece byte a byte preservado", self.before_local_database == file_hash(self.local_database))
        self.invariant("Log não expõe marcador interno de falha", "synthetic_sensitive_marker" not in self.server_log)
        self.invariant("Log não expõe credenciais sintéticas", all(value not in self.server_log for value in (PASSWORD, "changed-disposable-password", self.admin_token or "unused-marker")))
        exercised = {(r["method"], r["route"]) for r in self.results if "method" in r}
        missing = sorted(set(self.actual_inventory) - exercised)
        deviations = [r for r in self.results if any(not c["ok"] for c in r["checks"])]
        document = {"project": "task-manager-api", "target": "current working-tree sources",
                    "started_at_utc": self.started_at, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                    "versions": {"python": sys.version.split()[0], **{name: version(name) for name in ("flask", "flask-sqlalchemy", "flask-cors", "sqlalchemy", "werkzeug")}},
                    "sqlite": sqlite3.sqlite_version, "boot": {"command": f"{sys.executable} -B app.py", "ready": bool(self.admin_token), "host": "127.0.0.1"},
                    "isolation": "Temporary SQLite files; application and seed source from working tree; local database untouched",
                    "routes": self.actual_inventory, "routes_exercised": len(set(self.actual_inventory) & exercised),
                    "uncovered_routes": missing, "scenarios": len(self.results), "deviations": len(deviations),
                    "results": self.results, "query_measurements": self.query_measurements,
                    "source_hashes": self.before_sources, "notes": self.notes,
                    "baseline_limitations": self.baseline_limitations,
                    "limitations": ["No line coverage, load or concurrency measurement; query-growth measurements use isolated Flask test-client requests, functional scenarios use real HTTP."],
                    "error": error, "passed": not error and not deviations and not missing}
        output.parent.mkdir(parents=True, exist_ok=True)
        # JSON escapes retain rejected lone surrogates in recorded requests
        # without making UTF-8 evidence serialization fail on the test input.
        output.write_text(json.dumps(scrub(document), ensure_ascii=True, indent=2) + "\n",
                          encoding="utf-8")
        for result in deviations:
            print(f"FAIL {result['id']}: {result['name']}")
            for check in result["checks"]:
                if not check["ok"]:
                    print(json.dumps(scrub(check), ensure_ascii=True))
        print(f"HTTP routes: {document['routes_exercised']}/{len(self.actual_inventory)}; scenarios: {len(self.results)}; failures: {len(deviations)}")
        if error:
            print(f"Runner error: {error}")
        self.temp.cleanup()
        return 0 if document["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPOSITORY / "reports/evidence/validation-project-3.json")
    args = parser.parse_args()
    validation = Validation()
    error = None
    try:
        spec = importlib.util.spec_from_file_location("historical_scenarios", REPOSITORY / "scripts/baseline/project_3.py")
        scenarios = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scenarios)
        scenarios.run(validation)
        validation.extra_cases()
        validation.unicode_cases()
        validation.report_and_boundary_cases()
        validation.measure_queries()
    except Exception as exception:
        # Do not copy exception values: database errors can contain credentials.
        error = f"{type(exception).__name__} at {exception.__traceback__.tb_frame.f_code.co_name}"
        import traceback
        for frame in traceback.extract_tb(exception.__traceback__, limit=8):
            print(f"  {Path(frame.filename).name}:{frame.lineno} in {frame.name}")
    return validation.finish(args.output, error)


if __name__ == "__main__":
    raise SystemExit(main())
