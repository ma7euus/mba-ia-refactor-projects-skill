# Baseline — code-smells-project

- **Commit-base:** `6d1ce6248c3e956801010a89d8bdaab48029bf30`.
- **Execução (UTC):** 2026-10-30T02:09:49.449259+00:00.
- **Ambiente observado:** `{"python": "3.14.4", "flask": "3.1.1", "flask-cors": "5.0.1"}`.
- **Isolamento:** cópia do commit-base em diretório temporário; banco descartável; bancos locais preservados.
- **HTTP:** servidor real em loopback e porta efêmera. Flask executa o entry point por `runpy`, com debug e reloader desativados. Node carrega o entry point por `require`, com observador SQLite que aceita somente SELECT.
- **Código da aplicação preservado na execução:** sim.
- **Cobertura de operações:** 19/19 combinações método/rota.
- **Cenários:** 39; **cenários com desvios:** 12.

As expectativas representam o comportamento correto desejado. Um desvio documenta uma falha observada do legado; não é resultado a perpetuar na refatoração. Esta baseline não é o relatório da Fase 2 da skill.

Requisições, respostas completas sanitizadas, verificações e contagens de tabelas: [evidência JSON](evidence/baseline-project-1.json). Boot, avisos e erros: [log sanitizado](evidence/baseline-project-1.log).

## Operações inventariadas

| Método | Rota | Exercitada |
|---|---|---|
| DELETE | `/produtos/<int:id>` | Sim |
| GET | `/` | Sim |
| GET | `/health` | Sim |
| GET | `/pedidos` | Sim |
| GET | `/pedidos/usuario/<int:usuario_id>` | Sim |
| GET | `/produtos` | Sim |
| GET | `/produtos/<int:id>` | Sim |
| GET | `/produtos/busca` | Sim |
| GET | `/relatorios/vendas` | Sim |
| GET | `/usuarios` | Sim |
| GET | `/usuarios/<int:id>` | Sim |
| POST | `/admin/query` | Sim |
| POST | `/admin/reset-db` | Sim |
| POST | `/login` | Sim |
| POST | `/pedidos` | Sim |
| POST | `/produtos` | Sim |
| POST | `/usuarios` | Sim |
| PUT | `/pedidos/<int:pedido_id>/status` | Sim |
| PUT | `/produtos/<int:id>` | Sim |

## Baseline por método e rota

Uma linha por cenário executado, identificado pelo ID e pelo nome na primeira coluna. Valores sensíveis permanecem mascarados. Contagens sem variação não comprovam ausência de updates; os checks de persistência informam os valores observados. A indicação de preservar se limita às verificações deste cenário.

| Método e rota | Entrada | Status observado | Campos relevantes da resposta | Efeito no banco | Comportamento correto a preservar ou falha a corrigir |
|---|---|---|---|---|---|
| `GET /`<br>**P1-01** — Página inicial | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 200 | `endpoints`: `{"health":"/health","login":"/login","pedidos":"/pedidos","produtos":"/produtos","relatorios":"/relatorios/vendas","usuarios":"/usuarios"}`; `mensagem="Bem-vindo à API da Loja"`; `versao="1.0.0"` | Contagens das tabelas sem variação. | Preservar HTTP 200 e o comportamento verificado de «Página inicial». |
| `GET /health`<br>**P1-02** — Health e estado inicial do banco | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 200 | `ambiente="producao"`; `counts`: `{"pedidos":0,"produtos":10,"usuarios":3}`; `database="connected"`; `db_path="loja.db"`; `debug=true`; `secret_key="[MASCARADO]"`; `status="ok"`; `versao="1.0.0"` | Contagens das tabelas sem variação. Check de persistência «Conexão com SQLite»: observado `"connected"`. | Preservar o health; corrigir a exposição de secret_key. |
| `GET /produtos`<br>**P1-03** — Listagem dos produtos seed | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 200 | `dados`: lista com 10 item(ns); campos: `ativo, categoria, criado_em, descricao, estoque, id, nome, preco`; `sucesso=true` | Contagens das tabelas sem variação. | Preservar HTTP 200 e o comportamento verificado de «Listagem dos produtos seed». |
| `GET /produtos/2`<br>**P1-04** — Detalhe de produto existente | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 200 | `dados`: `{"ativo":1,"categoria":"informatica","criado_em":"2026-10-30 02:09:49","descricao":"Mouse sem fio ergonômico","estoque":50,"id":2,"nome":"Mouse Wireless","preco":89.9}`; `sucesso=true` | Contagens das tabelas sem variação. | Preservar HTTP 200 e o comportamento verificado de «Detalhe de produto existente». |
| `GET /produtos/999999`<br>**P1-05** — Produto inexistente | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 404 | `erro="Produto não encontrado"`; `sucesso=false` | Contagens das tabelas sem variação. | Preservar HTTP 404 e o comportamento verificado de «Produto inexistente». |
| `GET /produtos/busca`<br>**P1-06** — Busca por termo, categoria e preço | Query: `{"q":"Mouse","categoria":"informatica","preco_min":"80","preco_max":"100"}` | 200 | `dados`: lista com 1 item(ns); campos: `ativo, categoria, criado_em, descricao, estoque, id, nome, preco`; `sucesso=true`; `total=1` | Contagens das tabelas sem variação. | Preservar HTTP 200 e o comportamento verificado de «Busca por termo, categoria e preço». |
| `GET /produtos/busca`<br>**P1-07** — Filtro de preço com tipo inválido | Query: `{"preco_min":"abc"}` | 500 | `erro="could not convert string to float: 'abc'"` | Contagens das tabelas sem variação. | Corrigir a conversão inválida: retornar 400 em vez de 500. |
| `GET /usuarios`<br>**P1-08** — Listagem de usuários | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 200 | `dados`: lista com 3 item(ns); campos: `criado_em, email, id, nome, senha, tipo`; `sucesso=true` | Contagens das tabelas sem variação. | Preservar a listagem; remover senhas da resposta. |
| `GET /usuarios/1`<br>**P1-09** — Detalhe de usuário existente | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 200 | `dados`: `{"criado_em":"2026-10-30 02:09:49","email":"admin@loja.com","id":1,"nome":"Admin","senha":"[MASCARADO]","tipo":"admin"}`; `sucesso=true` | Contagens das tabelas sem variação. | Preservar o detalhe; remover a senha da resposta. |
| `GET /usuarios/999999`<br>**P1-10** — Usuário inexistente | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 404 | `erro="Usuário não encontrado"` | Contagens das tabelas sem variação. | Preservar HTTP 404 e o comportamento verificado de «Usuário inexistente». |
| `POST /usuarios`<br>**P1-11** — Criação de usuário de teste | JSON: `{"nome":"Pessoa Baseline","email":"baseline.loja@example.test","senha":"[MASCARADO]"}` | 201 | `dados`: `{"id":4}`; `sucesso=true` | Contagens: `usuarios`: 3 → 4. Check de persistência «Usuário persistido uma vez»: observado `1`. | Preservar cadastro com 201; substituir armazenamento da senha em texto puro. |
| `POST /usuarios`<br>**P1-12** — Usuário sem campos obrigatórios | JSON: `{"nome":"Incompleto"}` | 400 | `erro="Nome, email e senha são obrigatórios"` | Contagens das tabelas sem variação. | Preservar HTTP 400 e o comportamento verificado de «Usuário sem campos obrigatórios». |
| `POST /login`<br>**P1-13** — Login válido | JSON: `{"email":"baseline.loja@example.test","senha":"[MASCARADO]"}` | 200 | `dados`: `{"email":"baseline.loja@example.test","id":4,"nome":"Pessoa Baseline","tipo":"cliente"}`; `mensagem="Login OK"`; `sucesso=true` | Contagens das tabelas sem variação. | Preservar HTTP 200 e o comportamento verificado de «Login válido». |
| `POST /login`<br>**P1-14** — Login com senha incorreta | JSON: `{"email":"baseline.loja@example.test","senha":"[MASCARADO]"}` | 401 | `erro="Email ou senha inválidos"`; `sucesso=false` | Contagens das tabelas sem variação. | Preservar HTTP 401 e o comportamento verificado de «Login com senha incorreta». |
| `POST /login`<br>**P1-15** — Login sem campos obrigatórios | JSON: `{}` | 400 | `erro="Email e senha são obrigatórios"` | Contagens das tabelas sem variação. | Preservar HTTP 400 e o comportamento verificado de «Login sem campos obrigatórios». |
| `POST /produtos`<br>**P1-16** — Criação de produto de teste | JSON: `{"nome":"Produto Baseline","descricao":"Registro descartável","preco":25.0,"estoque":12,"categoria":"geral"}` | 201 | `dados`: `{"id":11}`; `mensagem="Produto criado"`; `sucesso=true` | Contagens: `produtos`: 10 → 11. Check de persistência «Produto persistido uma vez»: observado `1`. Check de persistência «Preço persistido»: observado `25.0`. Check de persistência «Estoque persistido»: observado `12`. | Preservar HTTP 201 e o comportamento verificado de «Criação de produto de teste». |
| `PUT /produtos/11`<br>**P1-17** — Edição de produto de teste | JSON: `{"nome":"Produto Baseline Editado","descricao":"Registro descartável","preco":27.5,"estoque":15,"categoria":"geral"}` | 200 | `mensagem="Produto atualizado"`; `sucesso=true` | Contagens das tabelas sem variação. Check de persistência «Edição persistida»: observado `{"nome":"Produto Baseline Editado","preco":27.5,"estoque":15}`. | Preservar HTTP 200 e o comportamento verificado de «Edição de produto de teste». |
| `POST /produtos`<br>**P1-18** — Produto com preço negativo | JSON: `{"nome":"Produto Baseline","descricao":"Registro descartável","preco":-1,"estoque":12,"categoria":"geral"}` | 400 | `erro="Preço não pode ser negativo"` | Contagens das tabelas sem variação. | Preservar HTTP 400 e o comportamento verificado de «Produto com preço negativo». |
| `POST /produtos`<br>**P1-19** — Produto com preço textual | JSON: `{"nome":"Produto Baseline","descricao":"Registro descartável","preco":"abc","estoque":12,"categoria":"geral"}` | 500 | `erro="'<' not supported between instances of 'str' and 'int'"` | Contagens das tabelas sem variação. | Validar o tipo de preco e retornar 400 em vez de 500. |
| `POST /produtos`<br>**P1-20** — Produto com apóstrofo no nome | JSON: `{"nome":"Caderno d'água","descricao":"Registro descartável","preco":25.0,"estoque":12,"categoria":"geral"}` | 500 | `erro="near \"água\": syntax error"` | Contagens das tabelas sem variação. | Aceitar o nome como dado e retornar 201; corrigir a montagem de SQL por concatenação. |
| `PUT /produtos/999999`<br>**P1-21** — Edição de produto inexistente | JSON: `{"nome":"Produto Baseline","descricao":"Registro descartável","preco":25.0,"estoque":12,"categoria":"geral"}` | 404 | `erro="Produto não encontrado"` | Contagens das tabelas sem variação. | Preservar HTTP 404 e o comportamento verificado de «Edição de produto inexistente». |
| `POST /pedidos`<br>**P1-22** — Pedido válido com dois itens do mesmo produto | JSON: `{"usuario_id":4,"itens":[{"produto_id":2,"quantidade":2}]}` | 201 | `dados`: `{"pedido_id":1,"total":179.8}`; `mensagem="Pedido criado com sucesso"`; `sucesso=true` | Contagens: `itens_pedido`: 0 → 1; `pedidos`: 0 → 1. Check de persistência «Estoque reduzido pela quantidade pedida»: observado `48`. Check de persistência «Pedido persistido»: observado `1`. Check de persistência «Total persistido»: observado `179.8`. Check de persistência «Uma linha de item persistida»: observado `1`. Check de persistência «Quantidade persistida»: observado `2`. | Preservar HTTP 201 e o comportamento verificado de «Pedido válido com dois itens do mesmo produto». |
| `GET /pedidos`<br>**P1-23** — Listagem geral de pedidos | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 200 | `dados`: lista com 1 item(ns); campos: `criado_em, id, itens, status, total, usuario_id`; `sucesso=true` | Contagens das tabelas sem variação. | Preservar HTTP 200 e o comportamento verificado de «Listagem geral de pedidos». |
| `GET /pedidos/usuario/4`<br>**P1-24** — Pedidos do usuário | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 200 | `dados`: lista com 1 item(ns); campos: `criado_em, id, itens, status, total, usuario_id`; `sucesso=true` | Contagens das tabelas sem variação. | Preservar HTTP 200 e o comportamento verificado de «Pedidos do usuário». |
| `PUT /pedidos/1/status`<br>**P1-25** — Aprovação de pedido | JSON: `{"status":"aprovado"}` | 200 | `mensagem="Status atualizado"`; `sucesso=true` | Contagens das tabelas sem variação. Check de persistência «Status aprovado persistido»: observado `"aprovado"`. | Preservar HTTP 200 e o comportamento verificado de «Aprovação de pedido». |
| `PUT /pedidos/1/status`<br>**P1-26** — Status de pedido inválido | JSON: `{"status":"inventado"}` | 400 | `erro="Status inválido"` | Contagens das tabelas sem variação. | Preservar HTTP 400 e o comportamento verificado de «Status de pedido inválido». |
| `PUT /pedidos/999999/status`<br>**P1-27** — Atualização de pedido inexistente | JSON: `{"status":"enviado"}` | 200 | `mensagem="Status atualizado"`; `sucesso=true` | Contagens das tabelas sem variação. | Retornar 404 em vez de informar sucesso para um pedido inexistente. |
| `GET /relatorios/vendas`<br>**P1-28** — Relatório após pedido aprovado | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 200 | `dados`: `{"desconto_aplicavel":0,"faturamento_bruto":179.8,"faturamento_liquido":179.8,"pedidos_aprovados":1,"pedidos_cancelados":0,"pedidos_pendentes":0,"ticket_medio":179.8,"total_pedidos":1}`; `sucesso=true` | Contagens das tabelas sem variação. | Preservar HTTP 200 e o comportamento verificado de «Relatório após pedido aprovado». |
| `POST /pedidos`<br>**P1-29** — Pedido com estoque insuficiente | JSON: `{"usuario_id":4,"itens":[{"produto_id":2,"quantidade":49}]}` | 400 | `erro="Estoque insuficiente para Mouse Wireless"`; `sucesso=false` | Contagens das tabelas sem variação. Check de persistência «Pedido recusado não persistido»: observado `1`. Check de persistência «Estoque preservado»: observado `48`. | Preservar HTTP 400 e o comportamento verificado de «Pedido com estoque insuficiente». |
| `POST /pedidos`<br>**P1-30** — Pedido com produto inexistente | JSON: `{"usuario_id":4,"itens":[{"produto_id":999999,"quantidade":1}]}` | 400 | `erro="Produto 999999 não encontrado"`; `sucesso=false` | Contagens das tabelas sem variação. | Preservar HTTP 400 e o comportamento verificado de «Pedido com produto inexistente». |
| `POST /pedidos`<br>**P1-31** — Pedido sem itens | JSON: `{"usuario_id":4,"itens":[]}` | 400 | `erro="Pedido deve ter pelo menos 1 item"` | Contagens das tabelas sem variação. | Preservar HTTP 400 e o comportamento verificado de «Pedido sem itens». |
| `POST /pedidos`<br>**P1-32** — Pedido com quantidade negativa | JSON: `{"usuario_id":4,"itens":[{"produto_id":2,"quantidade":-2}]}` | 201 | `dados`: `{"pedido_id":2,"total":-179.8}`; `mensagem="Pedido criado com sucesso"`; `sucesso=true` | Contagens: `itens_pedido`: 1 → 2; `pedidos`: 1 → 2. Check de persistência «Quantidade negativa não altera estoque»: observado `50` (divergente do esperado). | Rejeitar com 400 sem criar pedido nem aumentar estoque; o legado retorna 201 e total negativo. |
| `POST /pedidos`<br>**P1-33** — Pedido para usuário inexistente | JSON: `{"usuario_id":999999,"itens":[{"produto_id":2,"quantidade":1}]}` | 201 | `dados`: `{"pedido_id":3,"total":89.9}`; `mensagem="Pedido criado com sucesso"`; `sucesso=true` | Contagens: `itens_pedido`: 2 → 3; `pedidos`: 2 → 3. Check de persistência «Pedido órfão não persistido»: observado `1` (divergente do esperado). | Rejeitar a relação inválida com 400/404, sem persistir pedido órfão. |
| `DELETE /produtos/11`<br>**P1-34** — Exclusão de produto de teste | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 200 | `mensagem="Produto deletado"`; `sucesso=true` | Contagens: `produtos`: 11 → 10. Check de persistência «Produto removido do banco»: observado `0`. | Preservar HTTP 200 e o comportamento verificado de «Exclusão de produto de teste». |
| `DELETE /produtos/11`<br>**P1-35** — Exclusão repetida de produto | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 404 | `erro="Produto não encontrado"` | Contagens das tabelas sem variação. | Preservar HTTP 404 e o comportamento verificado de «Exclusão repetida de produto». |
| `DELETE /produtos/999999`<br>**P1-36** — Exclusão de produto inexistente | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 404 | `erro="Produto não encontrado"` | Contagens das tabelas sem variação. | Preservar HTTP 404 e o comportamento verificado de «Exclusão de produto inexistente». |
| `POST /admin/query`<br>**P1-37** — Consulta administrativa sem autorização | JSON: `{"sql":"SELECT COUNT(*) AS total FROM produtos"}` | 200 | `dados`: lista com 1 item(ns); campos: `total`; `sucesso=true` | Contagens das tabelas sem variação. | Exigir autenticação/autorização e restringir a execução de SQL; a consulta foi aceita anonimamente. |
| `POST /admin/query`<br>**P1-38** — Consulta administrativa sem SQL | JSON: `{}` | 400 | `erro="Query não informada"` | Contagens das tabelas sem variação. | Preservar HTTP 400 e o comportamento verificado de «Consulta administrativa sem SQL». |
| `POST /admin/reset-db`<br>**P1-39** — Reset administrativo sem autorização (último cenário) | JSON: `{}` | 200 | `mensagem="Banco de dados resetado"`; `sucesso=true` | Contagens: `itens_pedido`: 3 → 0; `pedidos`: 3 → 0; `produtos`: 10 → 0; `usuarios`: 4 → 0. | Negar operação anônima com 401/403; o legado apagou os dados do banco descartável. |

## Desvios observados

- **P1-02 — Health e estado inicial do banco:** HTTP 200; verificações reprovadas: Resposta omite campos de senha/hash/segredo; Health não expõe segredo.
- **P1-07 — Filtro de preço com tipo inválido:** HTTP 500; Entrada inválida deve ser rejeitada com 400, sem erro interno.
- **P1-08 — Listagem de usuários:** HTTP 200; verificações reprovadas: Resposta omite campos de senha/hash/segredo; Listagem não expõe senhas.
- **P1-09 — Detalhe de usuário existente:** HTTP 200; verificações reprovadas: Resposta omite campos de senha/hash/segredo; Detalhe não expõe senha.
- **P1-11 — Criação de usuário de teste:** HTTP 201; verificações reprovadas: Senha não armazenada em texto puro.
- **P1-19 — Produto com preço textual:** HTTP 500; divergência de status ou contrato.
- **P1-20 — Produto com apóstrofo no nome:** HTTP 500; Um apóstrofo em nome comum deve ser persistido como dado, sem quebrar o SQL.
- **P1-27 — Atualização de pedido inexistente:** HTTP 200; divergência de status ou contrato.
- **P1-32 — Pedido com quantidade negativa:** HTTP 201; Quantidade negativa deve ser recusada sem criar pedido nem aumentar estoque; verificações reprovadas: Quantidade negativa não cria pedido; Quantidade negativa não altera estoque.
- **P1-33 — Pedido para usuário inexistente:** HTTP 201; A relação de usuário deve ser validada antes de persistir o pedido; verificações reprovadas: Pedido órfão não persistido.
- **P1-37 — Consulta administrativa sem autorização:** HTTP 200; Sem autenticação, uma rota administrativa deve negar a operação.
- **P1-39 — Reset administrativo sem autorização (último cenário):** HTTP 200; Sem autenticação, a exclusão dos dados deve ser negada; verificações reprovadas: Dados preservados contra reset sem autorização.

## Observações de comportamento

- GET /health expõe secret_key no JSON; o valor foi mascarado nas evidências.
- GET /produtos/busca?preco_min=abc retorna 500 por conversão numérica sem tratamento.
- GET /usuarios inclui senha em cada usuário; valores foram mascarados.
- POST /usuarios persiste a senha recebida em texto puro, confirmado por leitura do SQLite isolado.
- POST /produtos com preco textual retorna 500 em comparação de tipos incompatíveis.
- Nome comum com apóstrofo falha em POST /produtos (500), evidenciando SQL construído por concatenação; não houve payload de ataque.
- PUT /pedidos/999999/status informa sucesso para pedido inexistente, sem verificar linhas alteradas.
- POST /pedidos aceita quantidade negativa: retorna total negativo e persiste pedido, aumentando o estoque; criação e estoque foram confirmados no SQLite.
- POST /pedidos cria pedido com usuario_id inexistente; a integridade referencial não é aplicada.
- POST /admin/query executa consulta SQL sem autenticação/autorização; a baseline usou apenas SELECT COUNT(*).
- POST /admin/reset-db apaga as quatro tabelas sem autorização, confirmado pela contagem de registros antes/depois no banco isolado.

## Reprodução e limites

```bash
python3 scripts/baseline/run.py --project 1
```

Usa as dependências já instaladas em `.venv` de cada Flask e `node_modules` do LMS. A fonte é sempre o commit-base, não o código corrente. A configuração de rede/debug e a instrumentação pertencem ao executor, sem editar os fontes legados.

- A cobertura mede operações exercitadas, não cobertura de linhas, carga ou todos os caminhos possíveis.
- Dados sensíveis são mascarados nas evidências. IDs, timestamps, portas e datas relativas do seed podem variar entre execuções.
