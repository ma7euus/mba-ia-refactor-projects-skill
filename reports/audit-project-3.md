Executei as Fases 1 e 2 da `refactor-arch` no `task-manager-api`. A auditoria está pronta para revisão; **nenhum arquivo ou banco foi alterado**. A Fase 3 depende da aprovação prevista na skill e no passo a passo.

**Estado auditado**

- Projeto: `task-manager-api/`, no repositório `/home/mateus/projetos/mateus/mba/mba-ia-refactor-projects-skill`.
- HEAD: `4245cdd94eff763f412e58a5cdbd0bb34eb2bd87`.
- Commit-base do roteiro: `6d1ce6248c3e956801010a89d8bdaab48029bf30`.
- Fontes, requisitos e README do projeto coincidem com o commit-base. A skill foi adicionada posteriormente; o worktree está limpo.
- Coleta: 31/10/2026, UTC−03. Ferramenta: Codex; identificador exato do modelo indisponível.
- Destino proposto: `reports/audit-project-3.md`, na raiz do repositório.

Foram calculados hashes individuais dos 15 arquivos Python. O SHA-256 do manifesto ordenado, no formato `hash  caminho\n`, é:

```text
166012e0f0d49ebae15e01743394583e8a3799ab635cad489fff203f2f745fc0
```

**Análise do projeto**

| Campo | Resultado |
|---|---|
| Linguagem e runtime | Python; interpretador existente: `3.14.4`. |
| Framework | Flask `3.0.0`, Flask-SQLAlchemy `3.1.1` e Flask-Cors `4.0.0`, declarados e encontrados nos metadados instalados. |
| Outras dependências | SQLAlchemy instalado `2.1.6`; Werkzeug `3.1.9`. Marshmallow `3.20.1`, requests `2.31.0` e python-dotenv `1.0.0` declarados e instalados. Sem lockfile. |
| Domínio | Usuários, tarefas, categorias, login, estatísticas e relatórios de produtividade. |
| Persistência | SQLite em arquivo. A URI relativa `sqlite:///tasks.db` resolve para `instance/tasks.db` com essa versão da extensão. Versão do motor não verificada nesta fase. |
| Inicialização | Importar `app.py` executa `db.create_all()`. `seed.py` apaga os registros antes de repopular o banco. |
| Entrada | `app.py`; comando documentado: `python app.py`. |
| Arquitetura | Models e blueprints existentes, mas handlers acumulam regras, consultas, transações e serialização. |
| Inventário | 15 arquivos Python, 1.158 linhas físicas, incluindo comentários, linhas vazias e módulos de inicialização; 22 operações HTTP explícitas. |
| Exclusões | `.venv`, caches, banco, skill e evidências. Requisitos e documentação examinados separadamente. |
| Integrações | `NotificationService` contém SMTP real, mas não é chamado pelos fluxos da aplicação. |

A resolução do arquivo SQLite e o ciclo de vida da sessão foram conferidos na [documentação do Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/en/stable/changes/#version-3-0-0).

A [baseline existente](reports/baseline-project-3.md) foi executada sobre cópia isolada do commit-base em **30/10/2026, às 02:09:49 UTC**: **22/22 operações, 57 cenários e 12 cenários com desvios**. É evidência histórica; nesta auditoria não houve boot, seed, instalação ou requisição HTTP.

**Resumo dos achados**

| CRITICAL | HIGH | MEDIUM | LOW | Total |
|---:|---:|---:|---:|---:|
| 2 | 2 | 5 | 2 | **11** |

Os caminhos e linhas abaixo são relativos ao projeto e ao estado anterior à refatoração.

**F-01 — CRITICAL — Hash de senha exposto nas respostas**

- **Catálogo/local:** AP-02; `models/user.py:16–25`. Consumidores: `routes/user_routes.py:33–40`, `85–86`, `127–129` e `207–211`.
- **Evidência:** `User.to_dict()` inclui `password`. A baseline confirmou exposição no detalhe, cadastro, atualização e login.
- **Impacto:** entrega material de autenticação ao cliente e permite ataques offline. É uma falha de exposição, distinta do armazenamento inadequado de F-03.
- **Correção e verificação:** serializer público com campos explícitos, preservando os demais campos válidos. Conferir todas as respostas, inclusive erros, para ausência de senha e hash.

**F-02 — CRITICAL — Operações destrutivas e privilégios sem autorização**

- **Catálogo/local:** AP-13; `app.py:18–20`; `routes/user_routes.py:49–78`, `119–148`, `185–211`; `routes/task_routes.py:85–238`; `routes/report_routes.py:167–223`.
- **Evidência:** não há autenticação efetiva nem verificação de propriedade ou papel nas operações. O login retorna um token literal previsível, sem validação posterior. A baseline confirmou promoção anônima persistida, cadastro administrativo e exclusão de usuário com suas tarefas.
- **Impacto:** permite alteração de privilégios, leitura e exclusão de recursos alheios. Token fictício e ausência de checks integram a mesma falha de autorização.
- **Correção e verificação:** aproveitar `/login` para emitir credencial verificável e aplicar a política descrita adiante. Testar anônimo, token inválido/expirado, usuário comum, usuário inativo e administrador; negativas devem preservar os dados.

**F-03 — HIGH — Senhas armazenadas com MD5 sem salt**

- **Catálogo/local:** AP-05; `models/user.py:27–32`; consumidores em `routes/user_routes.py:74–82`, `114–117` e `197–205`.
- **Evidência:** geração e comparação de MD5 determinístico; armazenamento também verificado pela baseline.
- **Impacto:** proteção inadequada contra ataques de descoberta de senha.
- **Correção e verificação:** usar hash de senha do Werkzeug com salt. Para contas existentes, verificar o formato legado e substituir o MD5 após login correto. Testar transição, senha incorreta, novos hashes e preservação das contas.

**F-04 — HIGH — Regras, persistência e apresentação concentradas nas rotas**

- **Catálogo/local:** AP-04; `routes/task_routes.py:85–223`, `273–299`; `routes/user_routes.py:42–151`; `routes/report_routes.py:12–155`, `157–223`.
- **Evidência:** handlers validam, consultam, calculam produtividade e atraso, coordenam gravações e montam JSON. O módulo de relatórios também mantém categorias.
- **Impacto:** forte acoplamento entre HTTP, regras e dados, dificultando manutenção e testes.
- **Correção e verificação:** manter models e blueprints úteis; extrair controllers, acesso a dados, regras compartilhadas e serializers. Revisar dependências e exercitar as 22 operações.

**F-05 — MEDIUM — Configuração fixa e inicialização com efeitos implícitos**

- **Catálogo/local:** AP-02; `app.py:11–13`, `30–34`; `services/notification_service.py:7–10`; `seed.py:11–14`, `16–35`.
- **Evidência:** configuração e credenciais demonstrativas embutidas; debug habilitado no launcher; criação de tabelas ao importar; seed destrutivo com senhas fixas.
- **Contexto:** não há evidência de credenciais reais de produção nem de envio SMTP pelas rotas.
- **Impacto:** reduz controle sobre execução e aumenta o risco de alterar dados ao preparar o ambiente.
- **Correção e verificação:** configuração externa, debug desabilitado por padrão, inicialização e seed explícitos. Preservar o caminho do banco. Verificar importação sem criação de tabelas e boot configurado; manter notificações sem envio real.

**F-06 — MEDIUM — Consultas por elemento nas listagens e relatórios**

- **Catálogo/local:** AP-07; `routes/task_routes.py:14–57`; `routes/user_routes.py:12–24`; `routes/report_routes.py:53–68`, `157–165`.
- **Evidência:** consultas de usuário/categoria dentro do loop de tarefas, carregamento lazy de tarefas por usuário e consultas por usuário/categoria nos relatórios.
- **Impacto:** trabalho no banco cresce com o volume retornado. A identity map pode reduzir alguns acessos; não foi medida uma contagem exata de queries.
- **Correção e verificação:** eager loading, consultas em lote e agregações. Preservar entidades sem tarefas, campos e taxas; medir consultas com fixtures de tamanhos diferentes.

**F-07 — MEDIUM — Validação incompleta e divergente**

- **Catálogo/local:** AP-08; `routes/task_routes.py:92–114`, `140–144`, `166–213`, `260–264`; `routes/user_routes.py:44–65`, `98–125`; `routes/report_routes.py:169–180`, `196–202`.
- **Evidência:** operações como `len`, regex, comparação, `join` e `int` recebem valores sem validação de tipo. A baseline confirmou quatro respostas `500` para título/prioridade/filtros inválidos.
- **Impacto:** entradas incorretas provocam erro interno ou permitem estado inconsistente. Os demais exemplos são evidência estática, ainda sem execução.
- **Correção e verificação:** validar objeto JSON, tipos, limites, enums, IDs, datas, tags, cor e booleanos antes de alterar entidades. Entradas inválidas devem retornar `400`, sem gravações.

**F-08 — MEDIUM — Tratamento de erros disperso e incompleto**

- **Catálogo/local:** AP-10; `routes/task_routes.py:62–63`, `146–154`, `217–238`; `routes/user_routes.py:80–90`, `127–151`; `routes/report_routes.py:182–223`.
- **Evidência:** repetição de capturas genéricas; consultas e parte da validação ficam fora dessas fronteiras. A baseline registrou erros internos em HTML.
- **Impacto:** respostas inconsistentes e diagnóstico fragmentado. Capturar exceções não substitui a validação de F-07.
- **Correção e verificação:** erros de aplicação explícitos e tradução centralizada; rollback e resposta JSON genérica para falhas inesperadas. Injetar falha de persistência e conferir rollback, sanitização e disponibilidade da requisição seguinte.

**F-09 — MEDIUM — APIs deprecated confirmadas**

- **Catálogo:** AP-09.
- **Locais de `Query.get`:** `routes/task_routes.py:42–51`, `67`, `117–122`, `158`, `188–195`, `227`; `routes/user_routes.py:29`, `94`, `136`, `155`; `routes/report_routes.py:105`, `192`, `213`.
- **Locais de `datetime.utcnow`:** `models/user.py:14`; `models/category.py:11`; `models/task.py:15–16`, `52`; `routes/task_routes.py:31`, `72`, `215`, `285`; `routes/user_routes.py:172`; `routes/report_routes.py:35–45`, `71`, `133`; `seed.py:66–74`; `utils/helpers.py:38`; `services/notification_service.py:35`.
- **Evidência e impacto:** `Query.get()` é legacy/deprecated no SQLAlchemy 2.x; `utcnow()` está deprecated desde Python 3.12. A baseline também contém avisos de `utcnow()`. [SQLAlchemy](https://docs.sqlalchemy.org/en/21/orm/queryguide/query.html#sqlalchemy.orm.Query.get), [Python](https://docs.python.org/3.14/library/datetime.html#datetime.datetime.utcnow).
- **Correção e verificação:** usar `session.get()` e uma função de tempo baseada em UTC. Preservar a convenção UTC sem timezone nas colunas existentes, evitando mistura entre datas aware e naive; testar ausência de registros, atraso e janela de sete dias.

**F-10 — LOW — Políticas repetidas apesar de constantes existentes**

- **Catálogo/local:** AP-12; `routes/task_routes.py:96–114`, `166–184`; `utils/helpers.py:110–115`; `models/task.py:38–60`.
- **Evidência:** limites de título, prioridade padrão, estados e regra de atraso aparecem em implementações paralelas.
- **Impacto:** mudanças de regra podem produzir divergências entre criação, edição e relatórios.
- **Correção e verificação:** consolidar políticas em código efetivamente utilizado. Testar limites e a mesma regra de atraso em todos os consumidores.

**F-11 — LOW — Imports e helpers sem consumidor**

- **Catálogo/local:** AP-12; `app.py:7`; `routes/task_routes.py:7`; `routes/user_routes.py:6`; `routes/report_routes.py:7–8`; `utils/helpers.py:57–108`.
- **Evidência:** imports sem referências e `process_task_data()` sem chamadas. Em `app.py`, `datetime` é utilizado; os imports desnecessários são os demais daquele grupo.
- **Impacto:** dependências e caminhos paralelos dificultam a leitura.
- **Correção e verificação:** remover imports e implementações comprovadamente sem uso, após consolidar as regras. Conferir referências e boot.

Não foi confirmado SQL injection: o `like(f'%{query}%')` compõe uma expressão parametrizada do ORM. Também não há fundamento para classificar o objeto `db` como conexão global insegura ou afirmar gravações parciais nos handlers apenas por atribuições anteriores à validação.

**Comparação com a análise manual**

| Item do passo a passo | Finding | Resultado |
|---|---|---|
| P3-01 — MD5 | F-03 | Confirmado |
| P3-02 — N+1 | F-06 | Confirmado |
| P3-03 — Tipos inválidos | F-07 | Confirmado |
| P3-04 — Constantes repetidas | F-10 | Confirmado |
| P3-05 — Imports desnecessários | F-11 | Confirmado |

Foram confirmados os **cinco problemas manuais**. Os mínimos de cinco findings e um CRITICAL/HIGH foram atendidos.

**Refatoração MVC proposta**

```text
task-manager-api/
  app.py                  # factory, composição e launcher
  config.py
  database.py
  errors.py
  models/                 # entidades e acesso a dados
  controllers/            # coordenação dos casos de uso
  routes/                 # blueprints e adaptação HTTP
  views/serializers.py    # representação pública
  services/               # autenticação e regras compartilhadas
  seed.py                 # execução explícita e controlada
  tests/                  # validação do código corrente
```

Ordem proposta:

1. Salvar esta auditoria antes de editar os fontes.
2. Separar composição, configuração, erros e apresentação: F-01, F-04, F-05 e F-08.
3. Implementar senhas, autenticação e autorização: F-02 e F-03.
4. Consolidar validação, regras e APIs atuais: F-07, F-09 e F-10.
5. Otimizar consultas e remover código sem uso: F-06 e F-11.
6. Executar a matriz funcional e registrar resultados em `reports/validation-project-3.md` e `reports/evidence/validation-project-3.*`.

**Contratos de segurança propostos**

- `/` e `/health` continuam públicos.
- Cadastro público continua em `POST /users`, limitado a `role=user`; solicitar privilégios administrativos será rejeitado.
- `/login` preserva `message`, `user` e `token`, removendo o hash do usuário.
- O token será aleatório, com expiração de uma hora; somente seu digest ficará em uma nova tabela de sessões. Cada requisição consultará usuário, atividade e papel no servidor. Alteração de senha revogará as sessões.
- Usuário comum acessa seus próprios dados e tarefas. Listagens, buscas e estatísticas de tarefas ficam restritas às suas tarefas.
- Administrador acessa recursos globais; altera `role`/`active`, exclui usuários e mantém categorias. O papel `manager` não receberá poderes administrativos implicitamente.
- Usuários autenticados podem consultar categorias. Relatório individual exige ser o titular ou administrador; relatório geral e listagem de usuários exigem administrador.
- Criação de tarefa pelo usuário comum associa o próprio usuário; atribuição a terceiros exige administrador. Tarefas sem responsável ficam sob administração.
- Sem credencial válida: `401`; sem permissão: `403`. Os formatos de sucesso permanecem, exceto pela retirada de campos sensíveis.
- O administrador inicial será provisionado por comando local explícito, com senha externa; não haverá cadastro público capaz de conceder esse papel.

**Dados existentes**

O banco continuará em `instance/tasks.db`. A tabela de sessões será uma adição ao schema; não haverá recriação das tabelas existentes. Senhas MD5 serão migradas após autenticação correta, preservando contas e IDs.

A exclusão autorizada de usuário continuará removendo suas tarefas na mesma transação. Para categoria vinculada, a política proposta é preservar as tarefas e definir `category_id=null`, com verificação explícita.

Seeds e cenários destrutivos usarão bancos descartáveis. O banco local não será usado para regressão. Notificações permanecerão sem envio real.

**Matriz de operações e validação**

A tabela registra a baseline histórica e o comportamento proposto. `ID` representa o parâmetro inteiro da rota original. Erros de recurso inexistente serão verificados com credencial autorizada.

| Método e rota | Entrada | Status histórico | Resposta relevante | Efeito no banco | Preservar/corrigir |
|---|---|---|---|---|---|
| `GET /` | Nenhuma | 200 | `message`, `version` | Nenhum | Preservar público |
| `GET /health` | Nenhuma | 200 | `status`, `timestamp` | Nenhum | Preservar público |
| `GET /tasks` | Credencial | 200 | Lista, nomes relacionados, `overdue` | Nenhum | Preservar campos; filtrar por permissão |
| `POST /tasks` | Título, prioridade, relações, data, tags | 201; 400/404; tipos causaram 500 | Task criada | Inserção | Autorizar; tipos inválidos passam a 400 |
| `GET /tasks/ID` | ID | 200/404 | Task, `overdue` | Nenhum | Titular/admin; preservar ausência |
| `PUT /tasks/ID` | Campos editáveis | 200/404 | Task atualizada | Atualização | Autorizar; validar antes de alterar |
| `DELETE /tasks/ID` | ID | 200/404 | `message` | Exclusão | Titular/admin; comprovar remoção |
| `GET /tasks/search` | `q`, `status`, `priority`, `user_id` | 200; filtros inválidos causaram 500 | Lista | Nenhum | Restringir escopo; inválidos retornam 400 |
| `GET /tasks/stats` | Credencial | 200 | Totais e taxa | Nenhum | Escopo autorizado; conferir cálculos |
| `GET /users` | Credencial administrativa | 200 | Lista, `task_count` | Nenhum | Exigir admin; eliminar N+1 |
| `POST /users` | Nome, email, senha | 201/400/409 | Usuário | Inserção | Preservar cadastro; sem hash/privilégio público |
| `GET /users/ID` | ID | 200/404 | Usuário e tarefas | Nenhum | Titular/admin; retirar hash |
| `PUT /users/ID` | Perfil, senha; campos administrativos | 200/404 | Usuário | Atualização | Titular no perfil; admin em role/active |
| `DELETE /users/ID` | ID e credencial administrativa | 200/404 | `message` | Usuário e tarefas removidos | Preservar exclusão autorizada e atomicidade |
| `GET /users/ID/tasks` | ID | 200/404 | Lista, `overdue` | Nenhum | Titular/admin |
| `POST /login` | Email e senha | 200/400/401/403 | `message`, `user`, `token` | Legado sem alteração | Token real, sessão e eventual rehash |
| `GET /reports/summary` | Credencial administrativa | 200 | Totais, produtividade, atrasos | Nenhum | Preservar cálculos; exigir admin |
| `GET /reports/user/ID` | ID | 200/404 | `user`, `statistics` | Nenhum | Titular/admin |
| `GET /categories` | Credencial | 200 | Lista, `task_count` | Nenhum | Autenticar; preservar campos e contagens |
| `POST /categories` | Nome, descrição, cor | 201/400 | Categoria | Inserção | Admin; validar tipos e cor |
| `PUT /categories/ID` | Campos da categoria | 200/404 | Categoria | Atualização | Admin; validar criação e edição igualmente |
| `DELETE /categories/ID` | ID | 200/404 | `message` | Exclusão | Admin; testar categoria vinculada e desvinculada |

Após aprovação, a validação incluirá:

- Boot do código editado por `.venv/bin/python app.py`, em loopback e banco descartável.
- As **22 operações**, com adaptação dos 57 cenários históricos às correções aprovadas.
- Autorização permitida/negada, tokens inválidos/expirados, inatividade e revogação após troca de senha.
- Persistência por consulta direta, incluindo `active`, `role`, relações, exclusões e migração de senha.
- Falhas controladas para rollback e recuperação.
- Datas controladas para atraso e produtividade; medições de queries com volumes diferentes.
- Revisão final de cada finding, comandos, resultados e limites.

O executor de baseline usa `git archive` de um commit fixo. Será necessário validar os **fontes correntes**; repetir apenas esse executor não comprovaria a refatoração. Carga, concorrência e cobertura de linhas não estão demonstradas pela baseline.

**Posso salvar esta auditoria em `reports/audit-project-3.md` e iniciar a Fase 3 com a refatoração, as mudanças de contrato e o plano de validação apresentados?**

Essa confirmação é exigida pela [SKILL.md](/home/mateus/projetos/mateus/mba/mba-ia-refactor-projects-skill/task-manager-api/.agents/skills/refactor-arch/SKILL.md), que determina “Then stop and wait for an explicit answer”, e pelo [passo a passo](/home/mateus/projetos/mateus/mba/mba-ia-refactor-projects-skill/PLANO_EXECUCAO.md:324), que exige “Exiba o relatório e pare para revisão humana”. A aprovação ocorre após a apresentação do relatório e antes de qualquer gravação.
