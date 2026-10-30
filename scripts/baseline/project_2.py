"""HTTP and persistence observations for the legacy LMS API."""


def _counts(b):
    row = b.node_query(
        "SELECT (SELECT COUNT(*) FROM users) AS users, "
        "(SELECT COUNT(*) FROM courses) AS courses, "
        "(SELECT COUNT(*) FROM enrollments) AS enrollments, "
        "(SELECT COUNT(*) FROM payments) AS payments, "
        "(SELECT COUNT(*) FROM audit_logs) AS audit_logs"
    )
    return row[0] if row else {}


def _delta(before, after, key):
    if key not in before or key not in after:
        return None
    return after[key] - before[key]


def _revenue(result):
    body = result.get("body")
    if not isinstance(body, list):
        return None
    return sum(item.get("revenue", 0) for item in body if isinstance(item, dict))


def _students(result, name):
    body = result.get("body")
    if not isinstance(body, list):
        return None
    return sum(
        student.get("student") == name
        for course in body
        if isinstance(course, dict)
        for student in course.get("students", [])
        if isinstance(student, dict)
    )


def _checkout(name, email, course=1, card="4-baseline-simulated", password=True):
    payload = {"usr": name, "eml": email, "c_id": course, "card": card}
    if password:
        payload["pwd"] = "synthetic-baseline-password"
    return payload


def run(b):
    b.inventory(
        [
            ("POST", "/api/checkout"),
            ("GET", "/api/admin/financial-report"),
            ("DELETE", "/api/users/:id"),
        ]
    )
    b.start_node()
    b.add_limitation(
        "Pagamento é simulado localmente pelo prefixo do campo card; não houve "
        "gateway, cartão real, SMTP nem serviço externo. SELECTs de observação "
        "usam o mesmo SQLite em memória do processo, sem alterar os dados."
    )

    initial_counts = _counts(b)
    initial_report = b.case(
        "Relatório financeiro com os dados iniciais",
        "GET",
        "/api/admin/financial-report",
        expected=200,
        expectation="Dois cursos; receita inicial total de 997 e uma matrícula paga.",
    )
    b.check(initial_report, "Receita inicial", _revenue(initial_report), 997)
    b.check(initial_report, "Estado inicial das tabelas", initial_counts, {
        "users": 1,
        "courses": 2,
        "enrollments": 1,
        "payments": 1,
        "audit_logs": 0,
    })

    paid_email = "baseline-paid@example.test"
    paid_name = "Baseline Paid Student"
    before = _counts(b)
    paid = b.case(
        "Checkout aprovado de usuário novo",
        "POST",
        "/api/checkout",
        payload=_checkout(paid_name, paid_email),
        expected=200,
        expectation="Cria usuário, matrícula, pagamento PAID e registro de auditoria.",
    )
    after = _counts(b)
    for key in ("users", "enrollments", "payments", "audit_logs"):
        b.check(paid, f"Registros adicionados em {key}", _delta(before, after, key), 1)
    enrollment_id = (
        paid["body"].get("enrollment_id")
        if isinstance(paid.get("body"), dict)
        else None
    )
    payment = b.node_query(
        "SELECT amount, status FROM payments WHERE enrollment_id = ?",
        (enrollment_id,),
    )
    b.check(paid, "Pagamento persistido", payment, [{"amount": 997.0, "status": "PAID"}])
    paid_users = b.node_query("SELECT id FROM users WHERE email = ?", (paid_email,))
    paid_user_id = paid_users[0]["id"] if paid_users else None
    paid_report = b.case(
        "Relatório após checkout aprovado",
        "GET",
        "/api/admin/financial-report",
        expected=200,
        expectation="Receita total de 1994 e inclusão do aluno sintético.",
    )
    b.check(paid_report, "Receita após compra", _revenue(paid_report), 1994)
    b.check(paid_report, "Aluno incluído no relatório", _students(paid_report, paid_name), 1)

    before = _counts(b)
    existing = b.case(
        "Checkout de usuário já cadastrado em outro curso",
        "POST",
        "/api/checkout",
        payload=_checkout(paid_name, paid_email, course=2),
        expected=200,
        expectation="Reutiliza o usuário e adiciona matrícula e pagamento de 497.",
    )
    after = _counts(b)
    b.check(existing, "Usuário não duplicado", _delta(before, after, "users"), 0)
    for key in ("enrollments", "payments", "audit_logs"):
        b.check(existing, f"Registros adicionados em {key}", _delta(before, after, key), 1)

    before = _counts(b)
    denied = b.case(
        "Checkout com pagamento recusado",
        "POST",
        "/api/checkout",
        payload=_checkout("Baseline Denied Student", "baseline-denied@example.test", card="5-baseline-simulated"),
        expected=400,
        expectation="Informa recusa e não cria matrícula nem pagamento.",
    )
    after = _counts(b)
    for key in ("enrollments", "payments", "audit_logs"):
        b.check(denied, f"Sem gravação em {key}", _delta(before, after, key), 0)
    b.note(denied, f"Efeito legado observado: variação de usuários = {_delta(before, after, 'users')}; criação ocorre antes da recusa.")

    before = _counts(b)
    missing = b.case(
        "Checkout sem campos obrigatórios",
        "POST",
        "/api/checkout",
        payload={"usr": "Baseline Missing Fields"},
        expected=400,
        expectation="Rejeita entrada incompleta sem persistir registros.",
    )
    b.check(missing, "Estado do banco preservado", _counts(b), before)

    before = _counts(b)
    unknown = b.case(
        "Checkout com curso inexistente",
        "POST",
        "/api/checkout",
        payload=_checkout("Baseline Unknown Course", "baseline-unknown@example.test", course=999999),
        expected=404,
        expectation="Curso inexistente deve retornar 404 sem gravações.",
    )
    b.check(unknown, "Estado do banco preservado", _counts(b), before)

    before = _counts(b)
    no_password = b.case(
        "Checkout de usuário novo sem senha",
        "POST",
        "/api/checkout",
        payload=_checkout("Baseline No Password", "baseline-no-password@example.test", course=2, password=False),
        expected=400,
        expectation="Cadastro sem senha deve ser rejeitado; o legado usa uma senha padrão.",
    )
    after = _counts(b)
    b.note(no_password, f"Variações observadas: usuários={_delta(before, after, 'users')}, matrículas={_delta(before, after, 'enrollments')}, pagamentos={_delta(before, after, 'payments')}.")

    invalid_email = b.case(
        "Checkout com email malformado",
        "POST",
        "/api/checkout",
        payload=_checkout("Baseline Invalid Email", "invalid-email-baseline", course=2),
        expected=400,
        expectation="Email malformado deve ser rejeitado antes do cadastro.",
    )
    invalid_users = b.node_query(
        "SELECT COUNT(*) AS total FROM users WHERE email = ?", ("invalid-email-baseline",)
    )
    b.check(invalid_email, "Nenhum usuário com email inválido persistido", invalid_users, [{"total": 0}])

    unsecured = b.case(
        "Relatório administrativo sem autenticação",
        "GET",
        "/api/admin/financial-report",
        expected=[401, 403],
        expectation="Dados administrativos devem exigir autenticação/autorização.",
    )
    b.note(unsecured, "A resposta completa foi obtida sem cabeçalho Authorization ou sessão.")
    revenue_before_delete = _revenue(unsecured)

    if paid_user_id is not None:
        removed = b.case(
            "Exclusão de usuário sintético com matrículas",
            "DELETE",
            f"/api/users/{paid_user_id}",
            expected=200,
            expectation="Excluir usuário deve preservar integridade referencial ou rejeitar a operação.",
            route="/api/users/:id",
        )
        user_rows = b.node_query("SELECT COUNT(*) AS total FROM users WHERE id = ?", (paid_user_id,))
        orphaned = b.node_query(
            "SELECT COUNT(*) AS total FROM enrollments e "
            "LEFT JOIN users u ON u.id = e.user_id WHERE u.id IS NULL"
        )
        b.check(removed, "Usuário removido", user_rows, [{"total": 0}])
        b.check(removed, "Nenhuma matrícula órfã", orphaned, [{"total": 0}])
    else:
        b.add_limitation("O checkout não forneceu usuário persistido; a exclusão vinculada não pôde ser realizada.")

    after_delete = b.case(
        "Relatório após exclusão de usuário matriculado",
        "GET",
        "/api/admin/financial-report",
        expected=200,
        expectation="Relatório permanece acessível; observar o efeito da exclusão nas matrículas e receita.",
    )
    b.note(after_delete, f"Receita antes/depois da exclusão: {revenue_before_delete} / {_revenue(after_delete)}; alunos apresentados como Unknown: {_students(after_delete, 'Unknown')}.")

    before = _counts(b)
    delete_unknown = b.case(
        "Exclusão de usuário inexistente",
        "DELETE",
        "/api/users/999999",
        expected=404,
        expectation="Um usuário inexistente deve ser identificado sem alegar exclusão bem-sucedida.",
        route="/api/users/:id",
    )
    b.check(delete_unknown, "Estado do banco preservado", _counts(b), before)

    b.add_finding("O relatório financeiro é acessível sem autenticação/autorização.")
    b.add_finding("O checkout aceita cadastro sem senha e email malformado.")
    b.add_finding("A exclusão deixa matrículas e pagamentos ligados a usuário removido; o relatório usa Unknown.")
    b.add_finding("A exclusão de usuário inexistente responde sucesso.")
    b.add_finding("O checkout recusado cria o usuário antes de negar o pagamento; esse efeito deve ser considerado na decisão de atomicidade.")

    # This malformed input throws inside an asynchronous sqlite callback in the
    # legacy implementation. Keep it last so a process crash cannot hide CRUD.
    numeric_card = b.case(
        "Checkout com card numérico",
        "POST",
        "/api/checkout",
        payload=_checkout("Baseline Numeric Card", "baseline-numeric@example.test", card=4),
        expected=400,
        expectation="Tipo inválido deve retornar 400 sem encerrar o processo.",
    )
    b.check(numeric_card, "Sem TypeError no processo", b.has_log("TypeError"), False)
    b.note(numeric_card, "Cenário executado por último porque a exceção assíncrona pode encerrar o servidor legado.")
    if numeric_card.get("status") is None or b.has_log("TypeError"):
        b.add_finding("Card numérico provoca TypeError em startsWith e pode encerrar o processo em vez de retornar 400.")
    if b.has_log("Processando cartão"):
        b.add_finding("O log do checkout contém cartão sintético e chave de configuração; a evidência persistida deve mascarar ambos.")
