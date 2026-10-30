"""Cenários HTTP e verificações SQLite da baseline do Task Manager legado."""

import hashlib


ROUTES = [
    ("GET", "/"),
    ("GET", "/health"),
    ("GET", "/tasks"),
    ("POST", "/tasks"),
    ("GET", "/tasks/<int:task_id>"),
    ("PUT", "/tasks/<int:task_id>"),
    ("DELETE", "/tasks/<int:task_id>"),
    ("GET", "/tasks/search"),
    ("GET", "/tasks/stats"),
    ("GET", "/users"),
    ("POST", "/users"),
    ("GET", "/users/<int:user_id>"),
    ("PUT", "/users/<int:user_id>"),
    ("DELETE", "/users/<int:user_id>"),
    ("GET", "/users/<int:user_id>/tasks"),
    ("POST", "/login"),
    ("GET", "/reports/summary"),
    ("GET", "/reports/user/<int:user_id>"),
    ("GET", "/categories"),
    ("POST", "/categories"),
    ("PUT", "/categories/<int:cat_id>"),
    ("DELETE", "/categories/<int:cat_id>"),
]


def _object(result):
    body = result.get("body")
    return body if isinstance(body, dict) else {}


def _list(result):
    body = result.get("body")
    return body if isinstance(body, list) else []


def _count(b, table, where="", params=()):
    # table/where são constantes deste módulo, nunca entradas do cliente.
    rows = b.query(f"SELECT COUNT(*) AS count FROM {table} {where}", params)
    return rows[0]["count"] if rows else None


def _check_password_field(b, result, body=None):
    body = _object(result) if body is None else body
    exposed = isinstance(body, dict) and "password" in body
    b.check(result, "Resposta omite senha/hash", exposed, False)
    if exposed:
        b.note(result, "O serializer legado inclui o campo password; valor mascarado na evidência.")


def run(b):
    b.inventory(ROUTES)
    b.start_flask(seed=True)
    b.add_limitation(
        "Baseline funcional em banco descartável com seed legado. Não mede N+1, "
        "carga, concorrência nem cobertura de todas as combinações de entradas."
    )
    b.add_limitation(
        "Datas dos seeds são relativas à execução. As tasks sintéticas usam "
        "2000-01-01 para verificar atraso de forma controlada."
    )

    root = b.case("Página inicial", "GET", "/")
    b.check(root, "Domínio anunciado", _object(root).get("message"), "Task Manager API")
    health = b.case("Health após boot", "GET", "/health")
    b.check(health, "Status de saúde", _object(health).get("status"), "ok")

    tasks = b.case("Listagem inicial de tasks", "GET", "/tasks")
    b.check(tasks, "Seed contém dez tasks", len(_list(tasks)), 10)
    stats = b.case("Estatísticas iniciais", "GET", "/tasks/stats")
    b.check(stats, "Total informado igual ao SQLite", _object(stats).get("total"), _count(b, "tasks"))
    users = b.case("Listagem inicial de usuários", "GET", "/users")
    b.check(users, "Seed contém três usuários", len(_list(users)), 3)
    categories = b.case("Listagem inicial de categorias", "GET", "/categories")
    b.check(categories, "Seed contém quatro categorias", len(_list(categories)), 4)
    summary = b.case("Relatório geral inicial", "GET", "/reports/summary")
    b.check(
        summary,
        "Totais do relatório correspondem aos seeds",
        _object(summary).get("overview"),
        {"total_tasks": 10, "total_users": 3, "total_categories": 4},
    )

    detail = b.case(
        "Detalhe do usuário seed sem autenticação", "GET", "/users/1",
        route="/users/<int:user_id>",
    )
    _check_password_field(b, detail)
    b.check(detail, "Dados de usuário exigem autorização", detail["status"] in (401, 403), True)
    b.case(
        "Tasks do usuário seed", "GET", "/users/1/tasks",
        route="/users/<int:user_id>/tasks",
    )
    b.case(
        "Relatório do usuário seed", "GET", "/reports/user/1",
        route="/reports/user/<int:user_id>",
    )

    missing = 999999
    for name, path, pattern in [
        ("Task inexistente", f"/tasks/{missing}", "/tasks/<int:task_id>"),
        ("Usuário inexistente", f"/users/{missing}", "/users/<int:user_id>"),
        ("Tasks de usuário inexistente", f"/users/{missing}/tasks", "/users/<int:user_id>/tasks"),
        ("Relatório de usuário inexistente", f"/reports/user/{missing}", "/reports/user/<int:user_id>"),
    ]:
        b.case(name, "GET", path, expected=404, route=pattern)

    email = "baseline.task@example.test"
    password = "baseline-task-fixture"
    user_payload = {"name": "Baseline Task User", "email": email, "password": password}
    created_user = b.case("Criar usuário sintético", "POST", "/users", user_payload, expected=201)
    user_id = _object(created_user).get("id")
    _check_password_field(b, created_user)
    b.check(created_user, "Usuário persistido no SQLite", _count(b, "users", "WHERE email = ?", (email,)), 1)
    stored = b.query("SELECT id, password FROM users WHERE email = ?", (email,))
    if stored:
        user_id = user_id or stored[0]["id"]
        is_md5 = stored[0]["password"] == hashlib.md5(password.encode()).hexdigest()
        b.check(created_user, "Senha não utiliza MD5 determinístico", is_md5, False)
    b.case("Email duplicado", "POST", "/users", user_payload, expected=409)
    b.case(
        "Email inválido", "POST", "/users",
        {"name": "Invalid", "email": "invalido", "password": password}, expected=400,
    )
    b.case("Usuário sem campos obrigatórios", "POST", "/users", {}, expected=400)

    login = b.case("Login válido do usuário sintético", "POST", "/login", {"email": email, "password": password})
    login_body = _object(login)
    _check_password_field(b, login, login_body.get("user"))
    predictable = str(login_body.get("token", "")).startswith("fake-jwt-token-")
    b.check(login, "Token não é literal previsível", predictable, False)
    b.case("Login com senha incorreta", "POST", "/login", {"email": email, "password": "incorrect-fixture"}, expected=401)
    b.case("Login com dados vazios", "POST", "/login", {}, expected=400)

    created_category = b.case(
        "Criar categoria sintética", "POST", "/categories",
        {"name": "Baseline Category", "description": "Fixture descartável", "color": "#123456"},
        expected=201,
    )
    category_id = _object(created_category).get("id")
    b.check(created_category, "Categoria persistida", _count(b, "categories", "WHERE name = ?", ("Baseline Category",)), 1)
    if category_id is None:
        rows = b.query("SELECT id FROM categories WHERE name = ?", ("Baseline Category",))
        category_id = rows[0]["id"] if rows else None
    b.case("Categoria sem nome", "POST", "/categories", {}, expected=400)
    b.case(
        "Editar categoria inexistente", "PUT", f"/categories/{missing}",
        {"name": "Missing"}, expected=404, route="/categories/<int:cat_id>",
    )
    b.case(
        "Excluir categoria inexistente", "DELETE", f"/categories/{missing}",
        expected=404, route="/categories/<int:cat_id>",
    )
    if category_id is not None:
        category_edit = b.case(
            "Editar categoria sintética", "PUT", f"/categories/{category_id}",
            {"name": "Baseline Category Updated", "color": "#abcdef"},
            route="/categories/<int:cat_id>",
        )
        rows = b.query("SELECT name, color FROM categories WHERE id = ?", (category_id,))
        b.check(category_edit, "Nome e cor persistidos", rows, [{"name": "Baseline Category Updated", "color": "#abcdef"}])

    if user_id is not None:
        updated_user = b.case(
            "Editar nome de usuário", "PUT", f"/users/{user_id}",
            {"name": "Baseline Task User Updated"}, route="/users/<int:user_id>",
        )
        _check_password_field(b, updated_user)
        rows = b.query("SELECT name FROM users WHERE id = ?", (user_id,))
        b.check(updated_user, "Nome atualizado no SQLite", rows, [{"name": "Baseline Task User Updated"}])

    task_payload = {
        "title": "Baseline synthetic task", "description": "Task de regressão descartável",
        "status": "pending", "priority": 2, "user_id": user_id,
        "category_id": category_id, "due_date": "2000-01-01", "tags": ["baseline", "fixture"],
    }
    created_task = b.case("Criar task sintética", "POST", "/tasks", task_payload, expected=201)
    task_id = _object(created_task).get("id")
    b.check(created_task, "Task persistida", _count(b, "tasks", "WHERE title = ?", (task_payload["title"],)), 1)
    if task_id is None:
        rows = b.query("SELECT id FROM tasks WHERE title = ?", (task_payload["title"],))
        task_id = rows[0]["id"] if rows else None
    search = b.case(
        "Buscar task por texto e filtros", "GET",
        f"/tasks/search?q=Baseline&status=pending&priority=2&user_id={user_id or missing}",
        route="/tasks/search",
    )
    if task_id is not None:
        b.check(search, "Busca inclui task criada", task_id in [row.get("id") for row in _list(search)], True)
        task_detail = b.case(
            "Detalhe da task vencida", "GET", f"/tasks/{task_id}",
            route="/tasks/<int:task_id>",
        )
        b.check(task_detail, "Data fixa classificada como atrasada", _object(task_detail).get("overdue"), True)
        updated_task = b.case(
            "Concluir task sintética", "PUT", f"/tasks/{task_id}",
            {"status": "done", "priority": 1, "title": "Baseline completed task"},
            route="/tasks/<int:task_id>",
        )
        rows = b.query("SELECT status, priority FROM tasks WHERE id = ?", (task_id,))
        b.check(updated_task, "Status e prioridade persistidos", rows, [{"status": "done", "priority": 1}])
        completed = b.case(
            "Detalhe da task concluída", "GET", f"/tasks/{task_id}",
            route="/tasks/<int:task_id>",
        )
        b.check(completed, "Task concluída não está atrasada", _object(completed).get("overdue"), False)

    b.case("Task sem título", "POST", "/tasks", {"description": "Sem título"}, expected=400)
    b.case("Task com status inválido", "POST", "/tasks", {"title": "Invalid status", "status": "invalid"}, expected=400)
    b.case("Task com prioridade fora da faixa", "POST", "/tasks", {"title": "Invalid priority", "priority": 6}, expected=400)
    b.case("Task com prioridade textual", "POST", "/tasks", {"title": "Invalid type", "priority": "alta"}, expected=400)
    b.case("Task com título numérico", "POST", "/tasks", {"title": 123}, expected=400)
    b.case("Busca com prioridade inválida", "GET", "/tasks/search?priority=alta", expected=400, route="/tasks/search")
    b.case("Busca com usuário inválido", "GET", "/tasks/search?user_id=invalid", expected=400, route="/tasks/search")
    b.case(
        "Task com usuário inexistente", "POST", "/tasks",
        {"title": "Missing relation", "user_id": missing}, expected=404,
    )
    b.case(
        "Task com categoria inexistente", "POST", "/tasks",
        {"title": "Missing relation", "category_id": missing}, expected=404,
    )
    b.case("Task com data inválida", "POST", "/tasks", {"title": "Invalid date", "due_date": "31/13/2000"}, expected=400)
    b.case("Editar task inexistente", "PUT", f"/tasks/{missing}", {"status": "done"}, expected=404, route="/tasks/<int:task_id>")
    b.case("Excluir task inexistente", "DELETE", f"/tasks/{missing}", expected=404, route="/tasks/<int:task_id>")
    b.case("Editar usuário inexistente", "PUT", f"/users/{missing}", {"name": "Missing"}, expected=404, route="/users/<int:user_id>")
    b.case("Excluir usuário inexistente", "DELETE", f"/users/{missing}", expected=404, route="/users/<int:user_id>")

    if user_id is not None:
        b.case(
            "Inativar usuário sintético", "PUT", f"/users/{user_id}",
            {"active": False}, route="/users/<int:user_id>",
        )
        b.case("Login do usuário inativo", "POST", "/login", {"email": email, "password": password}, expected=403)
        b.case(
            "Reativar usuário sintético", "PUT", f"/users/{user_id}",
            {"active": True}, route="/users/<int:user_id>",
        )
        role_change = b.case(
            "Cliente promove usuário a admin sem autorização", "PUT", f"/users/{user_id}",
            {"role": "admin"}, expected=[401, 403], route="/users/<int:user_id>",
            expectation="Alteração de privilégio exige autorização administrativa.",
        )
        rows = b.query("SELECT role FROM users WHERE id = ?", (user_id,))
        promoted = bool(rows and rows[0]["role"] == "admin")
        b.check(role_change, "Solicitação anônima não promove role", promoted, False)

    admin = b.case(
        "Cadastro solicita role administrativa", "POST", "/users",
        {"name": "Baseline Admin Request", "email": "baseline.admin@example.test", "password": password, "role": "admin"},
        expected=[400, 403], expectation="Cadastro público não concede role administrativa fornecida pelo cliente.",
    )
    b.check(admin, "Cadastro não concede role admin", _object(admin).get("role") == "admin", False)
    admin_id = _object(admin).get("id")

    if task_id is not None:
        deleted_task = b.case("Excluir task sintética", "DELETE", f"/tasks/{task_id}", route="/tasks/<int:task_id>")
        b.check(deleted_task, "Task removida do SQLite", _count(b, "tasks", "WHERE id = ?", (task_id,)), 0)
    if user_id is not None:
        owned = b.case(
            "Criar task para validar exclusão do usuário", "POST", "/tasks",
            {"title": "Baseline cascade task", "user_id": user_id, "category_id": category_id}, expected=201,
        )
        b.note(owned, "Fixture usada para conferir o efeito da exclusão do usuário em suas tasks.")
        deleted_user = b.case("Excluir usuário e suas tasks", "DELETE", f"/users/{user_id}", route="/users/<int:user_id>")
        b.check(deleted_user, "Usuário removido", _count(b, "users", "WHERE id = ?", (user_id,)), 0)
        b.check(deleted_user, "Tasks do usuário removidas", _count(b, "tasks", "WHERE user_id = ?", (user_id,)), 0)
    if admin_id is not None:
        b.case("Remover cadastro de privilégio da fixture", "DELETE", f"/users/{admin_id}", route="/users/<int:user_id>")
    if category_id is not None:
        deleted_category = b.case("Excluir categoria sintética", "DELETE", f"/categories/{category_id}", route="/categories/<int:cat_id>")
        b.check(deleted_category, "Categoria removida", _count(b, "categories", "WHERE id = ?", (category_id,)), 0)

    final_summary = b.case("Relatório final após limpeza das fixtures", "GET", "/reports/summary")
    b.check(
        final_summary, "Contagens dos seeds preservadas",
        _object(final_summary).get("overview"),
        {"total_tasks": 10, "total_users": 3, "total_categories": 4},
    )

    b.add_finding(
        "Os checks de segurança distinguem respostas funcionais de comportamentos "
        "que precisam mudar: exposição de hash, MD5, token previsível e autorização. "
        "Os resultados efetivos estão registrados em cada cenário."
    )
