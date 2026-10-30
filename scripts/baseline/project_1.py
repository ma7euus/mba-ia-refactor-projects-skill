"""Cenários HTTP e de persistência do legado Flask de e-commerce."""


def _data(result):
    body = result.get("body")
    return body.get("dados") if isinstance(body, dict) else None


def _count(b, table):
    # Os nomes são constantes deste módulo, nunca entrada recebida pela API.
    return b.query(f"SELECT COUNT(*) AS total FROM {table}")[0]["total"]


def run(b):
    b.inventory([
        ("GET", "/"),
        ("GET", "/health"),
        ("GET", "/produtos"),
        ("GET", "/produtos/busca"),
        ("GET", "/produtos/<int:id>"),
        ("POST", "/produtos"),
        ("PUT", "/produtos/<int:id>"),
        ("DELETE", "/produtos/<int:id>"),
        ("GET", "/usuarios"),
        ("GET", "/usuarios/<int:id>"),
        ("POST", "/usuarios"),
        ("POST", "/login"),
        ("POST", "/pedidos"),
        ("GET", "/pedidos"),
        ("GET", "/pedidos/usuario/<int:usuario_id>"),
        ("PUT", "/pedidos/<int:pedido_id>/status"),
        ("GET", "/relatorios/vendas"),
        ("POST", "/admin/query"),
        ("POST", "/admin/reset-db"),
    ])
    b.start_flask(seed=False)

    result = b.case("Página inicial", "GET", "/")
    if isinstance(result["body"], dict):
        b.check(result, "Versão da API", result["body"].get("versao"), "1.0.0")

    result = b.case("Health e estado inicial do banco", "GET", "/health")
    if isinstance(result["body"], dict):
        body = result["body"]
        b.check(result, "Conexão com SQLite", body.get("database"), "connected")
        b.check(result, "Produtos seed", body.get("counts", {}).get("produtos"), 10)
        b.check(result, "Usuários seed", body.get("counts", {}).get("usuarios"), 3)
        b.check(result, "Pedidos iniciais", body.get("counts", {}).get("pedidos"), 0)
        exposed = bool(body.get("secret_key"))
        b.check(result, "Health não expõe segredo", exposed, False)
        if exposed:
            b.add_finding("GET /health expõe secret_key no JSON; o valor foi mascarado nas evidências.")

    result = b.case("Listagem dos produtos seed", "GET", "/produtos")
    if isinstance(_data(result), list):
        b.check(result, "Quantidade inicial de produtos", len(_data(result)), 10)

    result = b.case("Detalhe de produto existente", "GET", "/produtos/2", route="/produtos/<int:id>")
    if isinstance(_data(result), dict):
        b.check(result, "ID do produto", _data(result).get("id"), 2)
    b.case("Produto inexistente", "GET", "/produtos/999999", expected=404, route="/produtos/<int:id>")

    result = b.case(
        "Busca por termo, categoria e preço", "GET",
        "/produtos/busca?q=Mouse&categoria=informatica&preco_min=80&preco_max=100",
    )
    if isinstance(_data(result), list):
        b.check(result, "Busca retorna somente Mouse", [item.get("id") for item in _data(result)], [2])
    result = b.case(
        "Filtro de preço com tipo inválido", "GET", "/produtos/busca?preco_min=abc", expected=400,
        expectation="Entrada inválida deve ser rejeitada com 400, sem erro interno.",
    )
    if result["status"] == 500:
        b.add_finding("GET /produtos/busca?preco_min=abc retorna 500 por conversão numérica sem tratamento.")

    result = b.case("Listagem de usuários", "GET", "/usuarios")
    if isinstance(_data(result), list):
        exposed = any("senha" in item for item in _data(result) if isinstance(item, dict))
        b.check(result, "Listagem não expõe senhas", exposed, False)
        if exposed:
            b.add_finding("GET /usuarios inclui senha em cada usuário; valores foram mascarados.")
    result = b.case("Detalhe de usuário existente", "GET", "/usuarios/1", route="/usuarios/<int:id>")
    if isinstance(_data(result), dict):
        b.check(result, "Detalhe não expõe senha", "senha" in _data(result), False)
    b.case("Usuário inexistente", "GET", "/usuarios/999999", expected=404, route="/usuarios/<int:id>")

    password = "Baseline-local-only-42"
    email = "baseline.loja@example.test"
    result = b.case(
        "Criação de usuário de teste", "POST", "/usuarios",
        {"nome": "Pessoa Baseline", "email": email, "senha": password}, expected=201,
    )
    user_id = _data(result).get("id") if isinstance(_data(result), dict) else None
    rows = b.query("SELECT id, email, senha FROM usuarios WHERE email = ?", (email,))
    b.check(result, "Usuário persistido uma vez", len(rows), 1)
    if rows:
        user_id = rows[0]["id"]
        plaintext = rows[0]["senha"] == password
        b.check(result, "Senha não armazenada em texto puro", plaintext, False)
        if plaintext:
            b.add_finding("POST /usuarios persiste a senha recebida em texto puro, confirmado por leitura do SQLite isolado.")
    b.case("Usuário sem campos obrigatórios", "POST", "/usuarios", {"nome": "Incompleto"}, expected=400)

    result = b.case("Login válido", "POST", "/login", {"email": email, "senha": password})
    if isinstance(_data(result), dict) and user_id is not None:
        b.check(result, "Login identifica o usuário criado", _data(result).get("id"), user_id)
    b.case("Login com senha incorreta", "POST", "/login", {"email": email, "senha": "invalid-local-only"}, expected=401)
    b.case("Login sem campos obrigatórios", "POST", "/login", {}, expected=400)

    product = {"nome": "Produto Baseline", "descricao": "Registro descartável", "preco": 25.0,
               "estoque": 12, "categoria": "geral"}
    result = b.case("Criação de produto de teste", "POST", "/produtos", product, expected=201)
    rows = b.query("SELECT id, preco, estoque FROM produtos WHERE nome = ?", (product["nome"],))
    b.check(result, "Produto persistido uma vez", len(rows), 1)
    product_id = rows[0]["id"] if rows else None
    if rows:
        b.check(result, "Preço persistido", rows[0]["preco"], 25.0)
        b.check(result, "Estoque persistido", rows[0]["estoque"], 12)
    if product_id is not None:
        changed = dict(product, nome="Produto Baseline Editado", preco=27.5, estoque=15)
        result = b.case(
            "Edição de produto de teste", "PUT", f"/produtos/{product_id}", changed,
            route="/produtos/<int:id>",
        )
        rows = b.query("SELECT nome, preco, estoque FROM produtos WHERE id = ?", (product_id,))
        if rows:
            b.check(result, "Edição persistida", dict(rows[0]), {"nome": changed["nome"], "preco": 27.5, "estoque": 15})
    else:
        b.add_limitation("Criação do produto de teste falhou; não foi possível concluir edição/exclusão desse registro.")

    b.case("Produto com preço negativo", "POST", "/produtos", dict(product, preco=-1), expected=400)
    result = b.case("Produto com preço textual", "POST", "/produtos", dict(product, preco="abc"), expected=400)
    if result["status"] == 500:
        b.add_finding("POST /produtos com preco textual retorna 500 em comparação de tipos incompatíveis.")
    result = b.case(
        "Produto com apóstrofo no nome", "POST", "/produtos", dict(product, nome="Caderno d'água"), expected=201,
        expectation="Um apóstrofo em nome comum deve ser persistido como dado, sem quebrar o SQL.",
    )
    if result["status"] == 500:
        b.add_finding("Nome comum com apóstrofo falha em POST /produtos (500), evidenciando SQL construído por concatenação; não houve payload de ataque.")
    b.case("Edição de produto inexistente", "PUT", "/produtos/999999", product, expected=404, route="/produtos/<int:id>")

    chosen_user = user_id if user_id is not None else 1
    stock_rows = b.query("SELECT preco, estoque FROM produtos WHERE id = ?", (2,))
    stock_before = stock_rows[0]["estoque"]
    unit_price = stock_rows[0]["preco"]
    expected_total = round(unit_price * 2, 2)
    result = b.case(
        "Pedido válido com dois itens do mesmo produto", "POST", "/pedidos",
        {"usuario_id": chosen_user, "itens": [{"produto_id": 2, "quantidade": 2}]}, expected=201,
    )
    order_id = _data(result).get("pedido_id") if isinstance(_data(result), dict) else None
    if isinstance(_data(result), dict):
        b.check(result, "Total da resposta", round(_data(result).get("total", -1), 2), expected_total)
    stock_after = b.query("SELECT estoque FROM produtos WHERE id = ?", (2,))[0]["estoque"]
    b.check(result, "Estoque reduzido pela quantidade pedida", stock_after, stock_before - 2)
    if order_id is not None:
        rows = b.query("SELECT total, status, usuario_id FROM pedidos WHERE id = ?", (order_id,))
        b.check(result, "Pedido persistido", len(rows), 1)
        if rows:
            b.check(result, "Total persistido", round(rows[0]["total"], 2), expected_total)
            b.check(result, "Usuário do pedido", rows[0]["usuario_id"], chosen_user)
        items = b.query("SELECT quantidade, preco_unitario FROM itens_pedido WHERE pedido_id = ?", (order_id,))
        b.check(result, "Uma linha de item persistida", len(items), 1)
        if items:
            b.check(result, "Quantidade persistida", items[0]["quantidade"], 2)

    result = b.case("Listagem geral de pedidos", "GET", "/pedidos")
    if isinstance(_data(result), list) and order_id is not None:
        b.check(result, "Pedido criado presente", order_id in [item.get("id") for item in _data(result)], True)
    result = b.case(
        "Pedidos do usuário", "GET", f"/pedidos/usuario/{chosen_user}",
        route="/pedidos/usuario/<int:usuario_id>",
    )
    if isinstance(_data(result), list) and order_id is not None:
        b.check(result, "Pedido aparece para seu usuário", order_id in [item.get("id") for item in _data(result)], True)
    if order_id is not None:
        result = b.case(
            "Aprovação de pedido", "PUT", f"/pedidos/{order_id}/status", {"status": "aprovado"},
            route="/pedidos/<int:pedido_id>/status",
        )
        rows = b.query("SELECT status FROM pedidos WHERE id = ?", (order_id,))
        b.check(result, "Status aprovado persistido", rows[0]["status"] if rows else None, "aprovado")
        result = b.case(
            "Status de pedido inválido", "PUT", f"/pedidos/{order_id}/status", {"status": "inventado"}, expected=400,
            route="/pedidos/<int:pedido_id>/status",
        )
        rows = b.query("SELECT status FROM pedidos WHERE id = ?", (order_id,))
        b.check(result, "Status anterior preservado", rows[0]["status"] if rows else None, "aprovado")
    else:
        b.add_limitation("Pedido válido não retornou ID; atualização de status do pedido criado não foi exercitada.")
    result = b.case(
        "Atualização de pedido inexistente", "PUT", "/pedidos/999999/status", {"status": "enviado"}, expected=404,
        route="/pedidos/<int:pedido_id>/status",
    )
    if result["status"] == 200:
        b.add_finding("PUT /pedidos/999999/status informa sucesso para pedido inexistente, sem verificar linhas alteradas.")

    result = b.case("Relatório após pedido aprovado", "GET", "/relatorios/vendas")
    if isinstance(_data(result), dict):
        b.check(result, "Um pedido contabilizado", _data(result).get("total_pedidos"), 1)
        b.check(result, "Faturamento bruto", _data(result).get("faturamento_bruto"), expected_total)
        b.check(result, "Pedido aprovado contabilizado", _data(result).get("pedidos_aprovados"), 1)

    order_count = _count(b, "pedidos")
    current_stock = b.query("SELECT estoque FROM produtos WHERE id = ?", (2,))[0]["estoque"]
    result = b.case(
        "Pedido com estoque insuficiente", "POST", "/pedidos",
        {"usuario_id": chosen_user, "itens": [{"produto_id": 2, "quantidade": current_stock + 1}]}, expected=400,
    )
    b.check(result, "Pedido recusado não persistido", _count(b, "pedidos"), order_count)
    b.check(result, "Estoque preservado", b.query("SELECT estoque FROM produtos WHERE id = ?", (2,))[0]["estoque"], current_stock)
    b.case(
        "Pedido com produto inexistente", "POST", "/pedidos",
        {"usuario_id": chosen_user, "itens": [{"produto_id": 999999, "quantidade": 1}]}, expected=400,
    )
    b.case("Pedido sem itens", "POST", "/pedidos", {"usuario_id": chosen_user, "itens": []}, expected=400)
    result = b.case(
        "Pedido com quantidade negativa", "POST", "/pedidos",
        {"usuario_id": chosen_user, "itens": [{"produto_id": 2, "quantidade": -2}]}, expected=400,
        expectation="Quantidade negativa deve ser recusada sem criar pedido nem aumentar estoque.",
    )
    b.check(result, "Quantidade negativa não cria pedido", _count(b, "pedidos"), order_count)
    after_negative_stock = b.query("SELECT estoque FROM produtos WHERE id = ?", (2,))[0]["estoque"]
    b.check(result, "Quantidade negativa não altera estoque", after_negative_stock, current_stock)
    if result["status"] == 201:
        b.add_finding("POST /pedidos aceita quantidade negativa: retorna total negativo e persiste pedido, aumentando o estoque; criação e estoque foram confirmados no SQLite.")

    result = b.case(
        "Pedido para usuário inexistente", "POST", "/pedidos",
        {"usuario_id": 999999, "itens": [{"produto_id": 2, "quantidade": 1}]}, expected=[400, 404],
        expectation="A relação de usuário deve ser validada antes de persistir o pedido.",
    )
    orphan_count = b.query("SELECT COUNT(*) AS total FROM pedidos WHERE usuario_id = ?", (999999,))[0]["total"]
    b.check(result, "Pedido órfão não persistido", orphan_count, 0)
    if orphan_count:
        b.add_finding("POST /pedidos cria pedido com usuario_id inexistente; a integridade referencial não é aplicada.")

    if product_id is not None:
        result = b.case("Exclusão de produto de teste", "DELETE", f"/produtos/{product_id}", route="/produtos/<int:id>")
        b.check(result, "Produto removido do banco", len(b.query("SELECT id FROM produtos WHERE id = ?", (product_id,))), 0)
        b.case("Exclusão repetida de produto", "DELETE", f"/produtos/{product_id}", expected=404, route="/produtos/<int:id>")
    b.case("Exclusão de produto inexistente", "DELETE", "/produtos/999999", expected=404, route="/produtos/<int:id>")

    result = b.case(
        "Consulta administrativa sem autorização", "POST", "/admin/query",
        {"sql": "SELECT COUNT(*) AS total FROM produtos"}, expected=[401, 403],
        expectation="Sem autenticação, uma rota administrativa deve negar a operação.",
    )
    b.note(result, "Consulta somente de leitura, executada exclusivamente contra o banco descartável da baseline.")
    if result["status"] == 200:
        b.add_finding("POST /admin/query executa consulta SQL sem autenticação/autorização; a baseline usou apenas SELECT COUNT(*).")
    b.case("Consulta administrativa sem SQL", "POST", "/admin/query", {}, expected=400)

    counts_before_reset = {table: _count(b, table) for table in ("produtos", "usuarios", "pedidos", "itens_pedido")}
    result = b.case(
        "Reset administrativo sem autorização (último cenário)", "POST", "/admin/reset-db", {}, expected=[401, 403],
        expectation="Sem autenticação, a exclusão dos dados deve ser negada.",
    )
    counts_after_reset = {table: _count(b, table) for table in counts_before_reset}
    b.check(result, "Dados preservados contra reset sem autorização", counts_after_reset, counts_before_reset)
    b.note(result, "O reset foi o último cenário e atingiu somente o SQLite criado em diretório temporário; bancos do workspace não foram usados.")
    if result["status"] == 200 and all(count == 0 for count in counts_after_reset.values()):
        b.add_finding("POST /admin/reset-db apaga as quatro tabelas sem autorização, confirmado pela contagem de registros antes/depois no banco isolado.")
