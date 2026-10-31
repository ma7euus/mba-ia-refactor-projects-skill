Executei as Fases 1 e 2 da `refactor-arch` no `task-manager-api`, somente em leitura. O projeto já contém uma refatoração MVC não commitada. Encontrei **um defeito atual de validação** e pendências para concluir a validação dessa refatoração.

A auditoria abaixo descreve os fontes atuais; os 11 achados de [audit-project-3.md](/home/mateus/projetos/mateus/mba/mba-ia-refactor-projects-skill/reports/audit-project-3.md) pertencem ao legado.

**Estado auditado**

- Alvo: `task-manager-api/`, dentro do repositório informado.
- Commit-base do worktree: `4245cdd94eff763f412e58a5cdbd0bb34eb2bd87`.
- Coleta: 31/10/2026, UTC−03; ferramenta: Codex.
- Alterações preexistentes: aplicação, banco, models, rotas, seed, helpers e README modificados; serviço de notificação removido; configuração, controllers, repositories, autenticação, validações, views e testes ainda não rastreados.
- Destino proposto para esta auditoria: `reports/audit-project-3-current.md`, preservando a auditoria legada.

O snapshot é o conteúdo do worktree, não apenas o commit. O manifesto SHA-256 ordenado dos 34 arquivos Python da aplicação é:

```text
e2ed4f92253b517a9b581538a96f258ec2259b198e039acd5ebf3345fee120fe
```

Os hashes individuais estão no manifesto `source_hashes` da evidência existente, com estas duas substituições para representar os 36 arquivos Python atuais, incluindo testes:

```text
services/user_validation.py
66c2f321a5a2d85d8ea18493c057bf137dfe950f0cfc83a384e90b34e00232d4

tests/run_validation.py
2bf93bc560507c2b9cd070451ee30244a3139779626e4ae4f5bb39bdce883dd6
```

**Análise do projeto**

| Campo | Resultado |
|---|---|
| Stack | Python; Flask 3.0.0, Flask-SQLAlchemy 3.1.1 e Flask-Cors 4.0.0 declarados e encontrados nos metadados instalados |
| Runtime | Python do ambiente: 3.14.4; execução anterior também registrou 3.14.4 |
| Outras versões instaladas | SQLAlchemy 2.1.6 e Werkzeug 3.1.9; sem lockfile |
| Domínio | Usuários, tarefas, categorias, autenticação e relatórios |
| Persistência | SQLite; banco padrão em `instance/tasks.db`; sessões de autenticação persistidas |
| Inicialização | `app.py` compõe dependências; schema criado explicitamente por `init-db`; seed exige banco e senha externos |
| Arquitetura | Rotas adaptam HTTP; controllers coordenam operações; repositories consultam dados; services concentram regras; views selecionam campos públicos |
| Inventário | 34 arquivos Python da aplicação, 1.308 linhas físicas; 2 arquivos de teste, 807 linhas; 22 operações HTTP |
| Exclusões | Dependências, caches, bancos, skill e relatórios; contagem inclui comentários, linhas vazias e módulos vazios |

A inspeção atual identificou autorização por papel/propriedade, tokens aleatórios com expiração, serializers sem senha, migração de MD5 após login correto, rollback centralizado e consultas agregadas/eager loading. Isso é evidência estática; não houve novo boot nesta execução.

**Achados atuais**

| CRITICAL | HIGH | MEDIUM | LOW | Total |
|---:|---:|---:|---:|---:|
| 0 | 0 | 1 | 0 | **1** |

**C-01 — MEDIUM — Unicode inválido ultrapassa a validação de entrada**

- **Catálogo:** AP-08 — validação incompleta.
- **Local principal:** `services/user_validation.py:32–35` e `62–75`.
- **Fluxo relacionado:** `routes/user_routes.py:31–33` → `controllers/users.py:52–61` → `models/user.py:21–30`; autenticação em `services/authentication.py:26–40`; tratamento final em `errors.py:41–46`.
- **Evidência estática:** uma senha JSON contendo um surrogate isolado, como `abcd\uD800`, satisfaz as verificações de tipo e comprimento. A função de senha do Werkzeug instalado chama `password.encode()`, que não aceita esse caractere.
- **Impacto:** entrada inválida alcança uma exceção inesperada e o caminho de resposta `500`, em vez de `400`. Esse resultado ainda não foi exercitado por HTTP nesta execução.
- **Severidade:** moderada; há tratamento sanitizado e rollback. Não foi demonstrada exposição de credenciais ou gravação parcial.
- **Correção proposta:** compartilhar a validação de texto codificável em UTF-8 entre cadastro, edição e login; revisar os demais campos textuais persistidos.
- **Compatibilidade:** preservar acentos, emojis e credenciais legadas válidas. Rejeitar caracteres inválidos com `400`.
- **Verificação:** testar cadastro, atualização e login; conferir ausência de gravações nas negativas e sucesso com Unicode válido.

Não encontrei chamadas atuais a `Query.get()` ou `datetime.utcnow()`. Os fontes usam `session.get()` e o helper UTC compatível com o armazenamento existente.

**Comparação com o passo a passo**

| Problema manual do legado | Situação nos fontes atuais |
|---|---|
| P3-01 — MD5 | Hash atual nas gravações; MD5 restrito à verificação e migração de contas antigas |
| P3-02 — N+1 | Eager loading e agregações implementados |
| P3-03 — Tipos inválidos | Validação tipada implementada; C-01 identifica uma lacuna adicional |
| P3-04 — Constantes repetidas | Políticas principais centralizadas em `services/task_rules.py` |
| P3-05 — Imports desnecessários | Ocorrências apontadas no legado não permanecem nos locais originais |

Os mínimos de cinco achados e um CRITICAL/HIGH **não são sustentados pela auditoria atual**, pois o código já foi refatorado. A auditoria histórica registra esses problemas; a inspeção atual não substitui a demonstração de detecção no legado.

**Evidências e pendências**

A baseline histórica, executada sobre o commit legado `6d1ce6248c3e956801010a89d8bdaab48029bf30`, registrou 22 operações, 57 cenários e 12 cenários com desvios.

A validação posterior, de **31/10/2026 às 03:46 UTC**, registra:

- 22/22 operações exercitadas;
- 253 resultados e 894 verificações;
- zero desvios;
- 20 verificações adicionais de lifecycle/CLI aprovadas em arquivo separado.

Esses resultados são anteriores às alterações em `services/user_validation.py` e `tests/run_validation.py`. Portanto, não comprovam as últimas mudanças, incluindo os casos de credenciais legadas longas. A evidência de lifecycle também não registra hashes.

Além disso, `README.md:140–143` aponta para **`reports/validation-project-3.md`, que não existe**. Essas pendências precisam ser resolvidas antes de declarar a Fase 3 concluída.

**Plano proposto para a Fase 3**

1. Salvar esta auditoria em `reports/audit-project-3-current.md`, preservando o relatório legado.
2. Corrigir C-01 nas validações compartilhadas e adicionar regressões para Unicode inválido e válido.
3. Manter as camadas MVC existentes e os contratos de autorização, respostas públicas e persistência.
4. Executar os validadores sobre os fontes correntes, com bancos temporários.
5. Registrar versões e hashes nas evidências de lifecycle.
6. Criar `reports/validation-project-3.md`, vinculando os achados legados às correções e aos resultados efetivamente observados.

Não está prevista migração adicional de schema. Os testes usarão bancos descartáveis, preservando `instance/tasks.db`.

A matriz abaixo cobre as 22 operações. Os status são históricos; cada operação será novamente exercitada com as credenciais apropriadas.

| Método e rota | Entrada | Status histórico | Resposta relevante | Efeito no banco | Validação planejada |
|---|---|---|---|---|---|
| `GET /` | — | 200 | Identificação | Nenhum | Acesso público |
| `GET /health` | — | 200 | Estado e horário | Nenhum | Boot atual |
| `GET /tasks` | Credencial | 200 | Lista e relações | Nenhum | Escopo e consultas |
| `POST /tasks` | Campos da tarefa | 201/400/404; alguns tipos davam 500 | Tarefa | Inserção | Tipos, Unicode e autorização |
| `GET /tasks/<id>` | ID | 200/404 | Tarefa | Nenhum | Titular/admin |
| `PUT /tasks/<id>` | Campos editáveis | 200/404 | Tarefa | Atualização | Validação sem gravação parcial |
| `DELETE /tasks/<id>` | ID | 200/404 | Mensagem | Exclusão | Permissão e remoção |
| `GET /tasks/search` | Filtros | 200; filtros inválidos davam 500 | Lista | Nenhum | Filtros inválidos retornam 400 |
| `GET /tasks/stats` | Credencial | 200 | Estatísticas | Nenhum | Escopo e cálculos |
| `GET /users` | Admin | 200 | Lista e contagens | Nenhum | Autorização e consultas |
| `POST /users` | Nome, email, senha | 201/400/409 | Usuário público | Inserção | C-01, limites e privilégios |
| `GET /users/<id>` | ID | 200/404 | Usuário e tarefas | Nenhum | Titular/admin; sem hash |
| `PUT /users/<id>` | Perfil/senha | 200/404 | Usuário público | Atualização | C-01 e revogação de sessões |
| `DELETE /users/<id>` | ID e admin | 200/404 | Mensagem | Usuário, tarefas e sessões | Atomicidade |
| `GET /users/<id>/tasks` | ID | 200/404 | Lista | Nenhum | Titular/admin |
| `POST /login` | Email e senha | 200/400/401/403 | Usuário e token | Sessão; possível rehash | C-01 e credenciais legadas longas |
| `GET /reports/summary` | Admin | 200 | Relatório geral | Nenhum | Permissão, cálculos e consultas |
| `GET /reports/user/<id>` | ID | 200/404 | Relatório individual | Nenhum | Titular/admin e cálculos |
| `GET /categories` | Credencial | 200 | Lista e contagens | Nenhum | Autenticação e consultas |
| `POST /categories` | Campos da categoria | 201/400 | Categoria | Inserção | Admin e validação |
| `PUT /categories/<id>` | Campos editáveis | 200/404 | Categoria | Atualização | Admin e validação |
| `DELETE /categories/<id>` | ID e admin | 200/404 | Mensagem | Categoria removida; tarefas preservadas | Desvinculação e atomicidade |

Comandos previstos, dentro do projeto:

```bash
.venv/bin/python -B tests/run_validation.py --output ../reports/evidence/validation-project-3.json
.venv/bin/python -B tests/check_lifecycle.py --output ../reports/evidence/validation-project-3-lifecycle.json
```

O primeiro executor inicia `app.py` corrente em loopback. Serão conferidos boot, permissões, respostas, efeitos persistidos, rollback e crescimento das consultas. Carga, concorrência e cobertura de linhas permanecerão fora desta validação.

**Posso salvar esta auditoria em `reports/audit-project-3-current.md` e iniciar a Fase 3 com a correção e o plano de validação apresentados?**

Essa confirmação é exigida pela [SKILL.md](/home/mateus/projetos/mateus/mba/mba-ia-refactor-projects-skill/task-manager-api/.agents/skills/refactor-arch/SKILL.md), que determina “Then stop and wait for an explicit answer”, e pelo [passo a passo](/home/mateus/projetos/mateus/mba/mba-ia-refactor-projects-skill/PLANO_EXECUCAO.md:324): “Exiba o relatório e pare para revisão humana”. Nenhum arquivo foi alterado nesta execução.
