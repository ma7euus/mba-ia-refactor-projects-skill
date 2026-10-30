# Passo a passo — desafio refactor-arch

Este roteiro combina os requisitos do [README.md](README.md), as 18 aulas do arquivo `fullcycle_IA_Labs.json` e a leitura do código dos três projetos. O objetivo da entrega é demonstrar que **a mesma skill analisa, audita e refatora os três projetos para MVC, com aprovação humana e validação funcional**.

O documento é um plano de trabalho. A análise estática orientou os achados iniciais, e a baseline funcional já foi executada e registrada na etapa 4. As refatorações e suas validações posteriores ainda deverão ser realizadas. As referências de linhas abaixo correspondem ao código legado do commit-base registrado na etapa 3, comum aos três projetos deste repositório.

## 1. Entenda o que precisa ser entregue

| Entrega | Mínimo exigido |
|---|---|
| Análise manual no README | Por projeto: pelo menos 5 problemas, incluindo 1 CRITICAL ou HIGH, 2 MEDIUM e 2 LOW; explicar a relevância |
| Skill | Nome `refactor-arch`, arquivo `SKILL.md` e três fases sequenciais |
| Conhecimento de apoio | Cinco áreas em Markdown: análise de projeto, catálogo de anti-patterns, template de relatório, arquitetura MVC e playbook |
| Catálogo | Pelo menos 8 anti-patterns, com as quatro severidades representadas e detecção de APIs deprecated |
| Playbook | Pelo menos 8 transformações com exemplos de código antes/depois |
| Execução | As três fases nos três projetos; auditoria com pelo menos 5 findings e 1 CRITICAL ou HIGH em cada projeto |
| Aprovação | Fase 2 termina pedindo confirmação antes de modificar qualquer arquivo |
| Validação | Aplicações iniciam e todos os endpoints originais têm comportamento validado após a refatoração |
| Evidências | Três relatórios de auditoria, código refatorado commitado, comparações antes/depois, checklists e logs ou screenshots |
| Publicação | Fork público no GitHub com README contendo Análise Manual, Construção da Skill, Resultados e Como Executar |

Os mínimos são **por projeto**. A análise manual terá, portanto, pelo menos 15 problemas documentados no total. Três relatórios bons sem código refatorado, ou apenas um projeto funcionando, deixam a entrega incompleta.

## 2. Aplique as aulas ao desafio

O JSON contém transcrições das 18 aulas, mas nem todas têm resumo. A relação abaixo considera também as transcrições.

| Aula | O que aproveitar na execução |
|---|---|
| 1 — O que é uma skill | Empacotar um procedimento reutilizável; separar conhecimento estável de informações que precisam ser verificadas na execução |
| 2 — Frontmatter e progressive discloure | N1: metadados; N2: instruções; N3: referências e scripts carregados quando necessários |
| 3 — Arquitetura por trás da Skill | Entender descoberta, seleção e leitura das referências; essas etapas internas não substituem as três fases do desafio |
| 4 — Primeira skill | Criar uma versão mínima e confirmar que a ferramenta a encontra e executa |
| 5 — Frontmatter | Escrever `name` e uma `description` que indique quando usar, gatilhos, limites e resultado esperado |
| 6 — Framework de decisão — vira ou não skill | Justificar a skill pela repetição, pelo procedimento não óbvio e pela estabilidade do conhecimento |
| 7 — Melhorando description | Testar pedidos positivos e negativos e ajustar a descrição conforme os erros |
| 8 — Skill N3 | Mover conteúdo extenso para referências; usar coleta determinística para inventários quando isso ajudar |
| 9 — Conectando skill ao mundo externo | Referenciar políticas explicitamente e retestar; a integração com GitHub demonstrada é opcional aqui |
| 10 — Best practice — skills | Manter corpo curto, instruções imperativas, escopo coerente e versionamento |
| 11 — Orquestração de Skills e subskills | Definir entradas, saídas, ordem e condições de avanço; subskills não são requisito |
| 12 — Orquestração com script determinístico | Verificar regras mecânicas com evidência, arquivo, linha e exit code; adaptar os exemplos ao MVC e às duas stacks |
| 13 — Skills e subagents | Paralelizar leituras independentes se necessário; consolidar resultados antes de editar |
| 14 — Evalution skills | Avaliar separadamente acionamento e qualidade; comparar resultados com/sem skill e após ajustes |
| 15 — Evaluation trigger | Testar linguagem natural em sessões novas e separar casos usados no ajuste dos usados na avaliação final |
| 16 — Skill com MCP | Distinguir procedimento da skill e dados externos obtidos por ferramentas; MCP não é necessário nesta entrega |
| 17 — Evalution com promptfoo | Automatizar avaliações se houver tempo; priorizar boot, endpoints e evidência objetiva |
| 18 — Finalizando | Usar a recapitulação para conferir a solução completa |

Para começar, priorize as aulas 1–8 e 10. Use 11–12 ao organizar o fluxo e 14–15 ao avaliá-lo. MCP, subagents, promptfoo e integrações externas são aprofundamentos opcionais.

Três adaptações são importantes: o alvo do desafio é **MVC**, mesmo quando a demonstração da aula usa outra arquitetura; a skill deve ser a mesma nos três projetos, mesmo quando uma aula discute personalização por projeto; e basta escolher uma das ferramentas aceitas, sem implementar suporte simultâneo a três CLIs.

## 3. Prepare o repositório e escolha a ferramenta

Este roteiro adota **OpenAI Codex** como escolha prática para este ambiente. Se preferir seguir as aulas com Claude Code, a adaptação está ao final. Ambas são opções aceitas pelo enunciado.

No Codex, use `<projeto>/.agents/skills/refactor-arch/SKILL.md`. A invocação explícita pode usar `$refactor-arch`, e `/skills` permite selecionar uma skill. Confira essas convenções na [documentação oficial de Skills do Codex](https://learn.chatgpt.com/docs/build-skills).

Na raiz do repositório:

```bash
git status --short
git remote -v
git rev-parse HEAD
python3 --version
node --version
npm --version
codex --version
```

1. Garanta que a entrega ficará em um fork público seu.
2. Use o commit-base registrado abaixo para relacionar os findings ao estado auditado.
3. Crie uma branch de trabalho, por exemplo `feat/refactor-arch`.
4. Preserve alterações locais já existentes e evite incluir arquivos da IDE na entrega.
5. Crie `reports/` e, se desejar, `reports/evidence/` para guardar as evidências de execução.

**Registro do código legado:**

- **Commit-base:** `6d1ce6248c3e956801010a89d8bdaab48029bf30`.
- **Escopo:** `code-smells-project/`, `ecommerce-api-legacy/` e `task-manager-api/`, todos no mesmo repositório.
- **Uso nos relatórios:** registrar esse mesmo hash no campo `commit-base` das três auditorias; os arquivos e as linhas dos findings devem apontar para o código desse commit.

**Resultado esperado:** ferramenta configurada, repositório preparado e referência recuperável do código anterior à refatoração.

## 4. Execute os legados e registre uma baseline

Antes de criar a skill, conheça o comportamento real das APIs. Use um ambiente Python separado por projeto: as versões de Flask são diferentes.

| Projeto | Stack declarada | Porta | Banco e preparação |
|---|---|---|---|
| `code-smells-project` | Flask 3.1.1 e flask-cors 5.0.1 | 5000 | SQLite `loja.db`; tabelas e dados iniciais criados automaticamente |
| `ecommerce-api-legacy` | Node.js, Express e sqlite3 | 3000 | SQLite em memória; dados iniciais recriados a cada boot |
| `task-manager-api` | Flask 3.0.0 e Flask-SQLAlchemy 3.1.1 | 5000 | SQLite; rodar `seed.py` antes da primeira validação com dados |

No Node, confira a versão resolvida no lockfile e no ambiente, além do intervalo declarado no `package.json`. O nome da pasta sugere e-commerce, mas o domínio implementado é **LMS: cursos, matrículas e pagamentos**.

Execute os blocos abaixo a partir da raiz, um projeto por vez. Mantenha o servidor em um terminal e faça as requisições em outro. Encerre o processo antes de iniciar o próximo Flask, pois ambos usam a porta 5000.

**Projeto 1:**

```bash
cd code-smells-project
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

**Projeto 2:**

```bash
cd ecommerce-api-legacy
npm ci
npm start
```

**Projeto 3:**

```bash
cd task-manager-api
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python seed.py
.venv/bin/python app.py
```

O `seed.py` do Task Manager **apaga os registros existentes antes de popular o banco**. Use-o em banco de desenvolvimento descartável. Confirme o arquivo SQLite efetivamente utilizado: com a URI atual, ele normalmente fica em `instance/tasks.db`.

As tabelas de baseline estão preenchidas, com uma linha por cenário, nos relatórios:

- [Projeto 1 — E-commerce Flask](reports/baseline-project-1.md#baseline-por-método-e-rota).
- [Projeto 2 — LMS Express](reports/baseline-project-2.md#baseline-por-método-e-rota).
- [Projeto 3 — Task Manager Flask](reports/baseline-project-3.md#baseline-por-método-e-rota).

Abaixo, três registros reais da execução. Os IDs P1, P2 e P3 identificam o projeto correspondente. As tabelas completas incluem todos os 110 cenários, inclusive falhas e entradas inválidas.

| Método e rota | Entrada | Status observado | Campos relevantes da resposta | Efeito no banco | Comportamento correto a preservar ou falha a corrigir |
|---|---|---|---|---|---|
| `POST /produtos`<br>**P1-16** — Criação de produto de teste | JSON: `{"nome":"Produto Baseline","descricao":"Registro descartável","preco":25.0,"estoque":12,"categoria":"geral"}` | 201 | `dados`: `{"id":11}`; `mensagem="Produto criado"`; `sucesso=true` | Contagens: `produtos`: 10 → 11. Check de persistência «Produto persistido uma vez»: observado `1`. Check de persistência «Preço persistido»: observado `25.0`. Check de persistência «Estoque persistido»: observado `12`. | Preservar HTTP 201 e o comportamento verificado de «Criação de produto de teste». |
| `POST /api/checkout`<br>**P2-02** — Checkout aprovado de usuário novo | JSON: `{"usr":"Baseline Paid Student","eml":"baseline-paid@example.test","c_id":1,"card":"[MASCARADO]","pwd":"[MASCARADO]"}` | 200 | `msg="Sucesso"`; `enrollment_id=2` | Contagens: `audit_logs`: 0 → 1; `enrollments`: 1 → 2; `payments`: 1 → 2; `users`: 1 → 2. Check de persistência «Pagamento persistido»: observado `[{"amount":997,"status":"PAID"}]`. | Preservar: Cria usuário, matrícula, pagamento PAID e registro de auditoria. |
| `PUT /tasks/11`<br>**P3-31** — Concluir task sintética | JSON: `{"status":"done","priority":1,"title":"Baseline completed task"}` | 200 | `category_id=5`; `created_at="2026-10-30 02:09:50.655383"`; `description="Task de regressão descartável"`; `due_date="2000-01-01 00:00:00"`; `id=11`; `priority=1`; `status="done"`; `tags`: lista com 2 item(ns); `title="Baseline completed task"`; `updated_at="2026-10-30 02:09:50.662676"`; `user_id=4` | Contagens das tabelas sem variação. Check de persistência «Status e prioridade persistidos»: observado `[{"status":"done","priority":1}]`. | Preservar HTTP 200 e o comportamento verificado de «Concluir task sintética». |

Inventarie **todas as combinações de método e rota**, incluindo caminhos administrativos e casos de erro. Use `app.py`, os arquivos de rotas e `api.http` como fontes. As primeiras verificações podem ser:

```bash
# Com o projeto 1 rodando:
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:5000/health
curl -sS http://localhost:5000/produtos

# Com o projeto 2 rodando:
curl -sS http://localhost:3000/api/admin/financial-report

# Com o projeto 3 rodando:
curl -sS http://localhost:5000/health
curl -sS http://localhost:5000/tasks
curl -sS http://localhost:5000/categories
```

Essas chamadas são apenas um início; não cobrem todos os endpoints. No projeto 1, a resposta legada de `/health` contém configuração sensível, por isso o exemplo registra somente o status. Mascare segredos, senhas, hashes e dados de cartão ao salvar logs.

Os projetos legados do commit-base não possuem suíte de testes pronta; o Node também não possui `npm test`. Prepare verificações de contrato e de fluxo antes da refatoração, por requisições HTTP ou testes de integração. Registre falhas preexistentes, sem tratá-las como comportamento que precisa ser perpetuado.

**Resultado esperado:** três baselines reproduzíveis, com ambiente, comandos, entradas, respostas e efeitos observados.

**Baseline registrada:**

| Projeto | Relatório | Operações exercitadas | Cenários | Cenários com desvios |
|---|---|---|---|---|
| E-commerce Flask | [baseline-project-1.md](reports/baseline-project-1.md) | 19/19 | 39 | 12 |
| LMS Express | [baseline-project-2.md](reports/baseline-project-2.md) | 3/3 | 14 | 6 |
| Task Manager Flask | [baseline-project-3.md](reports/baseline-project-3.md) | 22/22 | 57 | 12 |

Foram executados 110 cenários cobrindo as 44 operações. Os 30 cenários com desvios documentam defeitos do legado; não representam 30 problemas únicos. JSONs e logs sanitizados estão em `reports/evidence/`, com versões reais, entradas, respostas e efeitos no banco.

O executor reproduz os testes sobre cópias do commit-base em diretórios temporários. Reutiliza as dependências locais e preserva os bancos existentes. Os servidores usam loopback e portas efêmeras; debug/reloader do Flask são desativados, e o LMS recebe um observador de SQLite limitado a SELECT, sem editar os fontes. Para repetir a baseline, execute na raiz:

```bash
python3 scripts/baseline/run.py
```

## 5. Faça e documente a análise manual

Leia os projetos antes de delegar a auditoria à skill. Registre no README, para cada problema: ID, severidade, arquivo e linhas, descrição, impacto e justificativa da classificação.

Os achados abaixo são um ponto de partida extraído do código existente. Confira-os na sua leitura e complete as justificativas. Eles já fornecem a distribuição mínima por projeto.

### Projeto 1 — code-smells-project

| ID | Severidade | Local no legado | Problema e impacto |
|---|---|---|---|
| P1-01 | CRITICAL | `models.py:105–111` | Email e senha concatenados em SQL no login; entrada do cliente pode alterar a consulta |
| P1-02 | MEDIUM | `models.py:171–200` | Consultas dentro de laços na montagem de pedidos; custo cresce no padrão N+1 |
| P1-03 | MEDIUM | `controllers.py:37–50` e `118–126` | Tipos e conversões numéricas não são protegidos adequadamente; entrada inválida pode virar erro 500 |
| P1-04 | LOW | `models.py:256–262` | Limiares e percentuais de desconto sem nomes; regra de negócio pouco explícita |
| P1-05 | LOW | `controllers.py:8`, `57` e `106` | Logs ad hoc com `print`, sem padrão de nível e contexto |

Expanda a análise para rotas administrativas sem proteção (`app.py:47–78`), exposição da configuração em `/health` (`controllers.py:285–289`), senhas em texto puro e conexão SQLite global.

### Projeto 2 — ecommerce-api-legacy

| ID | Severidade | Local no legado | Problema e impacto |
|---|---|---|---|
| P2-01 | CRITICAL | `src/AppManager.js:45` | Cartão e chave de pagamento registrados em log; exposição de dados sensíveis |
| P2-02 | MEDIUM | `src/AppManager.js:83–106` | Relatório faz consultas por curso e matrícula; padrão N+1 |
| P2-03 | MEDIUM | `src/AppManager.js:29–35` e `45–46` | Validação de presença sem conferir tipos; cartão não textual pode falhar em `startsWith` |
| P2-04 | LOW | `src/AppManager.js:29–33` | Abreviações como `u`, `e`, `p`, `cid` e `cc` dificultam a leitura |
| P2-05 | LOW | `src/utils.js:10`, `25` e `src/AppManager.js:2` | `totalRevenue` declarado, exportado e importado sem uso |

Expanda para a God Class `AppManager`, o suposto hash baseado em Base64, cache global, ausência de transação no checkout e exclusão que pode deixar relacionamentos órfãos.

### Projeto 3 — task-manager-api

| ID | Severidade | Local no legado | Problema e impacto |
|---|---|---|---|
| P3-01 | HIGH | `models/user.py:27–32` | MD5 sem salt para armazenamento de senhas; proteção inadequada |
| P3-02 | MEDIUM | `routes/task_routes.py:14–57` | Consultas de usuário e categoria por task; padrão N+1 |
| P3-03 | MEDIUM | `routes/task_routes.py:92–114` e `260–264` | Comparações e conversões assumem tipos corretos; prioridade inválida pode gerar erro 500 |
| P3-04 | LOW | `routes/task_routes.py:96–114` e `utils/helpers.py:112–115` | Limites de título 3/200 e prioridade padrão 3 repetidos, apesar de já existirem constantes correspondentes |
| P3-05 | LOW | `app.py:7` e `routes/task_routes.py:7` | Imports agrupados e não utilizados prejudicam a clareza |

Expanda para o serializer que expõe o hash da senha, token de login previsível, alteração de role sem autorização e regras de negócio concentradas nas rotas. A existência de `models/`, `routes/` e `services/` não prova separação adequada de responsabilidades.

**APIs deprecated:** há chamadas como `Task.query.get(...)` em `routes/task_routes.py:67`. A documentação do SQLAlchemy classifica `Query.get()` como legado e indica `Session.get()`; confirme a versão instalada e preserve o tratamento de registro inexistente ao migrar para `db.session.get(Model, id)`. [Referência oficial](https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.get).

`datetime.utcnow()` é deprecated a partir do Python 3.12; registre a versão do runtime antes de classificá-lo. A migração para datas com timezone exige revisar comparações, armazenamento e serialização em conjunto. [Referência oficial do Python](https://docs.python.org/3/library/datetime.html#datetime.datetime.utcnow).

Não invente uma ocorrência deprecated em cada stack para preencher o relatório: o catálogo deve saber detectá-la, mas cada finding precisa de evidência.

**Resultado esperado:** seção “Análise Manual” do README concluída para os três projetos antes da criação da skill.

## 6. Projete os arquivos da skill

Comece dentro do projeto 1:

```text
code-smells-project/
└── .agents/skills/refactor-arch/
    ├── SKILL.md
    └── references/
        ├── project-analysis.md
        ├── anti-patterns.md
        ├── audit-report-template.md
        ├── mvc-guidelines.md
        └── refactoring-playbook.md
```

| Arquivo | Conteúdo a escrever |
|---|---|
| `SKILL.md` | Frontmatter, escopo, três fases, referências de cada fase, pausa humana e critérios de conclusão |
| `project-analysis.md` | Detecção por manifests/imports, versões declaradas e resolvidas, banco, domínio, entry point, rotas e dependências entre camadas |
| `anti-patterns.md` | IDs estáveis, sinais concretos, severidade, impacto, falsos positivos, exemplos por stack e regra de confirmação de depreciações |
| `audit-report-template.md` | Resumo por severidade, findings ordenados, arquivo/linhas, evidência, impacto, recomendação e plano proposto |
| `mvc-guidelines.md` | Responsabilidades, direção das dependências, configuração, tratamento de erros e exemplos Flask/Express |
| `refactoring-playbook.md` | Pelo menos 8 transformações com código antes/depois, condições de aplicação, cuidados de compatibilidade e validação |

No inventário, exclua `.git/`, `.venv/`, `node_modules/`, arquivos gerados e o próprio material da skill da contagem de código da aplicação. Explique o critério de contagem.

Um frontmatter inicial possível é:

```yaml
---
name: refactor-arch
description: >-
  Analyzes and audits backend projects, then refactors their architecture to MVC
  after explicit human approval. Use for requests such as "audit this legacy
  API", "refactor this backend to MVC", or "find architectural code smells".
  Do not use for conceptual MVC questions or isolated naming changes.
  Produces a stack summary, severity-ranked audit, and validated refactoring.
---
```

Esse bloco é um ponto de partida, não a skill pronta. A descrição pode ser ajustada com pedidos reais em português e inglês. Use os metadados compatíveis com a ferramenta escolhida, sem transportar automaticamente campos específicos do Claude para o Codex.

Mantenha o corpo procedural. Diga **qual referência ler e em qual fase**. Não dependa de o agente descobrir sozinho os arquivos de apoio.

**Resultado esperado:** estrutura N3 com as cinco áreas obrigatórias cobertas, sem conhecimento extenso duplicado no corpo.

## 7. Escreva o catálogo e o playbook juntos

Use a tabela abaixo como backlog. A severidade deve seguir a escala do enunciado e o impacto demonstrado; categorias como God Class podem variar conforme o acúmulo de responsabilidades.

| ID | Anti-pattern e severidade inicial | Transformação a demonstrar no playbook |
|---|---|---|
| AP-01 | SQL Injection — CRITICAL | SQL concatenado → consultas parametrizadas |
| AP-02 | Segredos/dados sensíveis expostos — CRITICAL | Literais e respostas/logs sensíveis → configuração externa e saída sanitizada |
| AP-03 | God Class/God Module — CRITICAL ou HIGH | Classe multifunção → composição de models, controllers e routes por domínio |
| AP-04 | Regras pesadas nas rotas/controllers — HIGH | Regras e SQL no handler → fluxo no controller e regras/persistência nas camadas apropriadas |
| AP-05 | Senhas em texto puro ou hash inadequado — HIGH | Armazenamento inseguro → biblioteca apropriada de hash de senhas e verificação |
| AP-06 | Estado global mutável — HIGH | Estado compartilhado implícito → dependências com ciclo de vida definido |
| AP-07 | Queries N+1 — MEDIUM | Consultas por item → joins, carregamento antecipado ou agregações |
| AP-08 | Validação insuficiente — MEDIUM | Suposições sobre entrada → validação de tipos, limites e respostas 4xx |
| AP-09 | APIs deprecated — MEDIUM ou conforme impacto | Chamada obsoleta confirmada → equivalente recomendado para a versão instalada |
| AP-10 | Error handling disperso — MEDIUM | Capturas inconsistentes → exceções e tratamento centralizado |
| AP-11 | Nomes pouco claros — LOW | Abreviações ambíguas → nomes com significado de domínio |
| AP-12 | Magic numbers e código morto — LOW | Literais repetidos/itens sem uso → constantes nomeadas e remoção de código morto |

Para **pelo menos oito** dessas linhas, escreva exemplos reais de código antes/depois. Use exemplos em Python e JavaScript ao longo do playbook; explicar uma transformação apenas em prosa não atende ao requisito dos exemplos.

Para preservar o agnosticismo, descreva o sinal geral e depois mostre adaptações por stack. Não instrua a skill a procurar somente `AppManager.js`, tabelas específicas, nomes de clientes ou rotas destes projetos.

No template do relatório, inclua:

```text
Projeto, stack, versões verificadas, commit-base e escopo analisado
Resumo: CRITICAL / HIGH / MEDIUM / LOW / total
Finding: ID, categoria, severidade, arquivo e linhas originais
Evidência sanitizada, descrição, impacto e recomendação
Correspondência com a análise manual, quando aplicável
Estrutura MVC proposta e mudanças de contrato necessárias
Plano de validação e pedido de confirmação
```

**Resultado esperado:** catálogo com pelo menos oito anti-patterns nas quatro severidades e playbook com pelo menos oito pares de exemplos antes/depois.

## 8. Implemente as três fases e a pausa humana

### Fase 1 — Análise

1. Resolva a raiz do projeto-alvo e a raiz do repositório.
2. Leia `project-analysis.md` e inspecione código e manifests.
3. Detecte linguagem, framework, dependências, banco, domínio e arquitetura atual.
4. Mapeie rotas, módulos e acoplamentos; conte arquivos com critério explícito.
5. Imprima o resumo e indique incertezas que dependam de execução posterior.

### Fase 2 — Auditoria

1. Leia o catálogo e o template.
2. Examine as ocorrências no contexto; não transforme toda correspondência de texto em finding.
3. Produza o relatório ordenado por `CRITICAL → HIGH → MEDIUM → LOW`.
4. Relacione os problemas ao plano de transformação e à validação.
5. **Exiba o relatório e pare para revisão humana.**

Até essa confirmação, as fases devem ser somente leitura: não alterar código, instalar dependências, executar seeds ou iniciar aplicações que criem bancos. Para seguir literalmente “antes de modificar qualquer arquivo”, exiba o relatório na Fase 2 e salve sua cópia em `reports/` somente após a aprovação, antes de modificar o código.

Uma pergunta de encerramento possível é: “Posso salvar este relatório e iniciar a Fase 3 com o plano apresentado?”. Se a resposta for negativa, encerre sem refatorar. Não envie `y` automaticamente nem trate silêncio como aprovação.

### Fase 3 — Refatoração e validação

1. Após confirmação, salve a auditoria exibida, preservando linhas e commit do código anterior.
2. Leia as guidelines MVC e o playbook.
3. Extraia configuração, organize models, routes/views e controllers e centralize erros.
4. Refatore em incrementos por domínio, corrigindo os achados e verificando os fluxos afetados.
5. Inicie a aplicação, execute a matriz de endpoints e confira efeitos no banco.
6. Faça uma nova auditoria e relacione cada finding à correção e à evidência de validação.
7. Informe falhas ou limitações reais; só declare a fase concluída quando as verificações passarem.

Para APIs, as Views podem ser serializers/apresentação JSON e o registro de routes, conforme a convenção adotada. Controllers coordenam o fluxo; não concentre novamente neles toda a regra de negócio. Services são úteis quando necessários, preservando o alvo MVC.

No Task Manager, aproveite as camadas existentes e corrija suas responsabilidades. Evite reconstruir tudo apenas para reproduzir a árvore do exemplo.

**Resultado esperado:** três fases com entradas e saídas claras, confirmação observável e validação baseada em execução.

## 9. Execute e valide o projeto 1

Abra o Codex dentro de `code-smells-project/` e envie:

```text
$refactor-arch
Analise e audite o projeto atual. Apresente o relatório e aguarde minha
confirmação antes de modificar qualquer arquivo. Após aprovação, salve a
auditoria em reports/audit-project-1.md na raiz do repositório e execute
a refatoração MVC com a validação dos endpoints.
```

Confira o resumo da stack e os findings antes de aprovar. Neste projeto, o enunciado exige encontrar pelo menos cinco dos problemas documentados na análise manual. Se faltarem, ajuste os sinais e as referências e repita a auditoria.

Depois da confirmação e da refatoração, valide:

| Fluxo | Verificações |
|---|---|
| Boot, raiz e health | Inicialização e respostas corretas; health sem segredo |
| Produtos | Listagem, detalhe, busca, criação, edição e exclusão de produto de teste |
| Usuários e login | Criação, listagens/detalhe, credenciais válidas/inválidas; sem senha no payload |
| Pedidos | Criação, listagem geral/por usuário e atualização de status; totais e estoque corretos |
| Relatório | Vendas coerentes com os dados e pedidos criados |
| Casos inválidos | Tipos errados, IDs inexistentes, quantidade/estoque e valores fora de faixa |
| Rotas administrativas | Política explícita de autorização/restrição e teste dos casos permitidos e negados |

Preserve os contratos válidos da baseline. Supressão de senhas, exigência de autorização e bloqueio de SQL arbitrário são correções intencionais: registre-as e valide o comportamento seguro. Não mantenha vulnerabilidades apenas para reproduzir a resposta antiga.

Guarde o log de boot, resultados dos endpoints e estrutura antes/depois. Revise o diff e faça um commit do projeto 1, da skill e de suas evidências.

**Resultado esperado:** projeto 1 refatorado e funcionando, com `reports/audit-project-1.md` e evidências reais.

## 10. Reutilize a mesma skill nos projetos 2 e 3

Na raiz do repositório, copie a skill:

```bash
mkdir -p ecommerce-api-legacy/.agents/skills task-manager-api/.agents/skills
cp -R code-smells-project/.agents/skills/refactor-arch ecommerce-api-legacy/.agents/skills/
cp -R code-smells-project/.agents/skills/refactor-arch task-manager-api/.agents/skills/
```

Abra uma sessão dentro de cada projeto. Repita o prompt anterior, trocando o destino para `reports/audit-project-2.md` ou `reports/audit-project-3.md`, sempre na raiz do repositório. Confira a pausa humana em cada execução.

### Projeto 2 — LMS em Node.js/Express

Valide as três operações existentes:

1. `POST /api/checkout`: pagamento aprovado, recusado, curso inexistente e entradas inválidas. Confira matrícula e pagamento persistidos, além da resposta.
2. `GET /api/admin/financial-report`: receita e alunos por curso coerentes antes/depois do checkout.
3. `DELETE /api/users/:id`: exclusão de usuário de teste e integridade de matrículas/pagamentos conforme a política definida.

Use `api.http` como ponto de partida e dados sintéticos. O pagamento atual é simulado pelo código; não é necessário contratar gateway nem fornecer credenciais reais. Corrija o log que expõe cartão/chave antes de guardar evidências.

O banco reinicia vazio e recebe seeds a cada boot. Compare cenários que partam de estados equivalentes; não exclua o usuário seed antes de verificar os relatórios.

### Projeto 3 — Task Manager em Python/Flask

Valide todas as rotas de tasks, busca, estatísticas, usuários, login, relatórios e categorias, além de `/` e `/health`. Inclua criação, edição e exclusão com registros de teste.

Verifique especialmente tipos inválidos, registros inexistentes, permissões, ausência de hash no JSON e tratamento de chamadas deprecated. Use datas controladas para testar atrasos: os seeds calculam vencimentos relativos ao dia da execução.

O serviço de notificação existente não está integrado aos fluxos de rotas. A refatoração não deve começar a enviar emails reais para demonstrar funcionamento.

Faça um commit por projeto concluído. Se precisar melhorar a skill após um desses testes, sincronize as três cópias e confira novamente os cenários afetados. Quando a mudança afetar detecção, reavalie também uma cópia isolada do código legado; a auditoria de código já corrigido não demonstra capacidade de detectar os problemas originais.

Compare as cópias finais:

```bash
diff -r code-smells-project/.agents/skills/refactor-arch ecommerce-api-legacy/.agents/skills/refactor-arch
diff -r code-smells-project/.agents/skills/refactor-arch task-manager-api/.agents/skills/refactor-arch
```

**Resultado esperado:** mesma versão da skill nos três projetos, três auditorias e três aplicações validadas.

## 11. Avalie a skill e finalize a documentação

Avalie duas dimensões, como ensinado nas aulas 14–15:

| Dimensão | Como verificar |
|---|---|
| Qualidade da execução | Stack correta, findings reais com linhas, pausa humana, MVC e regressão funcional nos três projetos |
| Acionamento pela descrição | Pedidos em linguagem natural que devem ou não selecionar a skill, sem mencionar seu nome |

Exemplos positivos: “Audite esta API legada e proponha uma refatoração MVC” e “Encontre violações arquiteturais neste backend”. Exemplos negativos: “Explique o que é MVC” e “Renomeie esta variável”. Registre a ferramenta, a versão, o modelo e os erros observados. A invocação explícita prova o fluxo, mas não testa o roteamento pela `description`.

A avaliação de acionamento melhora a solução, mas não substitui os critérios de aceite do desafio. Scripts de verificação e promptfoo são opcionais; não podem substituir a aprovação humana nem os testes dos endpoints.

Atualize o README com as quatro seções exigidas:

| Seção | Conteúdo final |
|---|---|
| Análise Manual | Problemas dos três projetos, distribuição de severidades e justificativas |
| Construção da Skill | Estrutura, catálogo, decisões de design, agnosticismo, dificuldades e ajustes |
| Resultados | Contagens reais dos relatórios, estruturas antes/depois, checklist por projeto, logs/screenshots e comparação entre stacks |
| Como Executar | Pré-requisitos, caminho e invocação da skill, preparação das aplicações e comandos de validação |

Use o checklist completo do enunciado **uma vez por projeto**. Não marque itens com base em intenção. Para cada validação funcional, mantenha comando, cenário, resultado e evidência correspondentes.

Antes da publicação, confirme:

- [ ] Análise manual com pelo menos 5 problemas e a distribuição exigida em cada projeto.
- [ ] `refactor-arch/SKILL.md` e referências presentes nos três projetos, no caminho da ferramenta escolhida.
- [ ] Cinco áreas obrigatórias cobertas em Markdown.
- [ ] Catálogo com pelo menos 8 anti-patterns, as quatro severidades e detecção de APIs deprecated.
- [ ] Playbook com pelo menos 8 transformações e código antes/depois.
- [ ] Três execuções com evidência de pausa antes de qualquer escrita.
- [ ] Três auditorias em `reports/audit-project-{1,2,3}.md`, com pelo menos 5 findings e 1 CRITICAL ou HIGH cada.
- [ ] Auditorias identificam o estado anterior à refatoração e mantêm arquivo/linhas exatos.
- [ ] MVC, configuração externa, tratamento centralizado de erros e entry point claro nos três projetos.
- [ ] Boot e todos os endpoints validados; correções intencionais de contrato explicadas.
- [ ] Código refatorado e evidências commitados; README com as quatro seções completas.
- [ ] Fork público acessível e sem ambientes virtuais, bancos locais, arquivos da IDE ou valores sensíveis adicionados à entrega.

Não declare “zero anti-patterns” apenas porque o servidor iniciou. Relacione os findings às correções, reaudite o código final e registre o que efetivamente foi verificado. Se algum critério continuar falhando, faça nova iteração antes de concluir a entrega.

### Se preferir Claude Code

Mantenha o mesmo roteiro e os mesmos arquivos de conhecimento. Use `.claude/skills/refactor-arch/` dentro de cada projeto e a invocação apresentada no enunciado:

```bash
claude "/refactor-arch"
```

Adapte os caminhos dos comandos de cópia e documente a ferramenta escolhida no README. A sequência de trabalho permanece: **baseline → análise manual → construção da skill → auditoria → confirmação → refatoração → validação**, repetindo a execução nos três projetos.
