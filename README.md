# Entregável

Refatoração arquitetural dos três projetos legados para MVC usando a skill **`refactor-arch` no OpenAI Codex**. Esta seção reúne a análise manual, as decisões da skill, os resultados e os comandos de reprodução. O enunciado original foi preservado ao final para consulta.

**Situação verificada em 31/10/2026:** os quatro critérios mínimos de aceite foram atingidos nos **3/3 projetos**, conforme as auditorias e as evidências de validação: **32 findings no legado e 44/44 operações HTTP exercitadas após a refatoração**. A conferência dos SHA-256 das evidências contra os arquivos atuais confirmou **83 arquivos distintos, sem divergências**. Nesta revisão documental, as suítes não foram reexecutadas; os resultados abaixo são das execuções registradas.

| Acesso rápido | Conteúdo |
|---|---|
| [Análise Manual](#análise-manual) | Problemas, severidades e relevância por projeto |
| [Construção da Skill](#construção-da-skill) | Design, catálogo, portabilidade e desafios |
| [Resultados](#resultados) | Auditorias, estruturas, checklist, logs e aceite |
| [Como Executar](#como-executar) | Ambiente, invocação no Codex e validação |
| [Plano de execução](PLANO_EXECUCAO.md) | Roteiro detalhado e baseline histórica |

## Análise Manual

Os locais abaixo são relativos a cada projeto no **commit legado `6d1ce6248c3e956801010a89d8bdaab48029bf30`**, anterior às mudanças. Os arquivos removidos ou reorganizados podem ser consultados com `git show <commit>:<projeto>/<arquivo>`. A análise inicial está documentada no [passo 5 do plano](PLANO_EXECUCAO.md#5-faça-e-documente-a-análise-manual); as auditorias aprofundam os achados e relacionam cada ID manual a um finding.

### Projeto 1 — code-smells-project: E-commerce Python/Flask

| ID | Severidade | Local no legado | Problema e justificativa |
|---|---|---|---|
| P1-01 | CRITICAL | `models.py:105–111` | Email e senha concatenados em SQL no login: a entrada pode alterar a consulta e comprometer a autenticação. |
| P1-02 | MEDIUM | `models.py:171–200` | Consultas dentro de laços ao montar pedidos: o padrão N+1 aumenta o trabalho no banco conforme crescem pedidos e itens. |
| P1-03 | MEDIUM | `controllers.py:37–50,118–126` | Conversões numéricas sem validação de tipos: entradas inválidas geram 500 em vez de uma rejeição controlada. |
| P1-04 | LOW | `models.py:256–262` | Limiares e percentuais de desconto sem nomes: dificultam compreender e alterar a política comercial. |
| P1-05 | LOW | `controllers.py:8,57,106` | Diagnósticos com `print` dispersos: falta padronização de nível e contexto para manutenção. |

A [auditoria do projeto 1](reports/audit-project-1.md) também confirmou exposição de senhas/configuração, administração sem autorização, senhas textuais, conexão global e falhas de integridade. P1-03 passou a **HIGH** pelo impacto adicional no estoque; P1-05 foi consolidado no finding **MEDIUM** de erros/logs. Por isso, a distribuição da auditoria difere da análise inicial.

### Projeto 2 — ecommerce-api-legacy: LMS Node.js/Express

| ID | Severidade | Local no legado | Problema e justificativa |
|---|---|---|---|
| P2-01 | CRITICAL | `src/AppManager.js:45` | Cartão e chave de pagamento no log: expõem dados sensíveis a quem acessa os registros da aplicação. |
| P2-02 | MEDIUM | `src/AppManager.js:83–106` | Relatório consulta por curso e matrícula: N+1 eleva custo e latência com o volume de dados. |
| P2-03 | MEDIUM | `src/AppManager.js:29–35,45–46` | Verificação apenas de presença, sem tipos: um cartão numérico chega a `startsWith` e encerra o processo, como registrado na baseline. |
| P2-04 | LOW | `src/AppManager.js:29–33` | Nomes como `u`, `e`, `p`, `cid` e `cc` escondem o significado dos dados e dificultam revisar o checkout. |
| P2-05 | LOW | `src/utils.js:10,25`; `src/AppManager.js:2` | `totalRevenue` declarado, exportado e importado sem uso: acrescenta estado e dependências sem função real. |

A [auditoria do projeto 2](reports/audit-project-2.md) ampliou a análise para God Class, Base64 usado como suposto hash de senha, falta de autorização, checkout sem atomicidade e exclusões que deixam relacionamentos órfãos.

### Projeto 3 — task-manager-api: Task Manager Python/Flask

| ID | Severidade | Local no legado | Problema e justificativa |
|---|---|---|---|
| P3-01 | HIGH | `models/user.py:27–32` | MD5 sem salt para senhas: fornece proteção inadequada contra descoberta de credenciais. |
| P3-02 | MEDIUM | `routes/task_routes.py:14–57` | Busca de usuário e categoria por tarefa: N+1 aumenta consultas na listagem. |
| P3-03 | MEDIUM | `routes/task_routes.py:92–114,260–264` | Comparações e conversões presumem tipos corretos: prioridades e filtros inválidos podem gerar 500. |
| P3-04 | LOW | `routes/task_routes.py:96–114`; `utils/helpers.py:112–115` | Limites e prioridade padrão repetidos apesar das constantes existentes: alterações podem produzir regras divergentes. |
| P3-05 | LOW | `app.py:7`; `routes/task_routes.py:7` | Imports agrupados e não utilizados: prejudicam a clareza das dependências e a leitura. |

A [auditoria do projeto 3](reports/audit-project-3.md) também confirmou hash exposto em respostas, token previsível e operações sem autorização, regras nas rotas, erros dispersos e uso de `Query.get()`/`datetime.utcnow()` nas versões em que são APIs legadas/deprecated.

**Requisito da análise manual atendido:** cada projeto possui cinco problemas, com pelo menos um CRITICAL/HIGH, dois MEDIUM e dois LOW. As auditorias reconheceram os cinco IDs manuais de cada projeto, com as reclassificações justificadas acima.

## Construção da Skill

### Estrutura e decisões de design

A implementação principal está em [code-smells-project/.agents/skills/refactor-arch/SKILL.md](code-smells-project/.agents/skills/refactor-arch/SKILL.md), com cópias idênticas no [LMS](ecommerce-api-legacy/.agents/skills/refactor-arch/SKILL.md) e no [Task Manager](task-manager-api/.agents/skills/refactor-arch/SKILL.md). Cada cópia contém o `SKILL.md` e cinco referências Markdown; não depende de scripts, MCP ou subagentes para funcionar.

O `SKILL.md` usa frontmatter com nome e descrição dos gatilhos/limites de uso, seguido de três fases sequenciais. A **Fase 1** detecta stack, domínio, arquitetura e inventário de operações; a **Fase 2** confirma os achados, apresenta auditoria e plano e aguarda aprovação humana explícita; a **Fase 3** salva a auditoria aprovada, refatora incrementalmente e valida os fontes correntes. As duas primeiras fases são somente leitura, inclusive sem criar relatórios ou iniciar aplicações.

O conhecimento detalhado fica nas referências, carregadas conforme a fase, para manter o fluxo principal focado:

| Referência | Decisão e finalidade |
|---|---|
| [project-analysis.md](code-smells-project/.agents/skills/refactor-arch/references/project-analysis.md) | Detectar linguagem, framework, persistência e arquitetura por evidências; inventariar arquivos e método/rota antes de propor mudanças. |
| [anti-patterns.md](code-smells-project/.agents/skills/refactor-arch/references/anti-patterns.md) | Catálogo de 14 padrões com IDs estáveis, severidade, sinais, confirmação, impacto e proteção contra falsos positivos. |
| [audit-report-template.md](code-smells-project/.agents/skills/refactor-arch/references/audit-report-template.md) | Padronizar snapshot, versões, totais, locais exatos, evidências, comparação manual, plano e aprovação. |
| [mvc-guidelines.md](code-smells-project/.agents/skills/refactor-arch/references/mvc-guidelines.md) | Definir responsabilidades e dependências entre models, controllers, views/routes e serviços, com configuração e erros centralizados. |
| [refactoring-playbook.md](code-smells-project/.agents/skills/refactor-arch/references/refactoring-playbook.md) | Oferecer 14 transformações AP-01–AP-14 com exemplos antes/depois e verificações; os mesmos IDs conectam detecção e correção. |

### Anti-patterns incluídos e motivação

As severidades abaixo são padrões do catálogo; cada ocorrência recebe a classificação sustentada pelo impacto observado.

| ID | Anti-pattern | Severidade padrão | Por que incluído |
|---|---|---|---|
| AP-01 | SQL injection | CRITICAL | Impedir que entradas alterem consultas e autenticação. |
| AP-02 | Segredos/dados sensíveis expostos | CRITICAL | Cobrir configuração, serializers e logs que vazam credenciais. |
| AP-03 | God Class/God Module | HIGH | Separar responsabilidades concentradas, como no `AppManager`. |
| AP-04 | Regras/persistência em rotas ou controllers | HIGH | Tornar regras testáveis e reutilizáveis fora do transporte HTTP. |
| AP-05 | Armazenamento inseguro de senhas | HIGH | Corrigir texto puro, Base64 e MD5 com migração ou redefinição explícita. |
| AP-06 | Estado global mutável/ciclo de vida inadequado | HIGH | Definir propriedade, isolamento e fechamento de conexões e estado. |
| AP-07 | Consultas N+1 | MEDIUM | Evitar crescimento de acessos por item em listas e relatórios. |
| AP-08 | Validação ausente ou inconsistente | MEDIUM | Rejeitar tipos, faixas e relações inválidos antes de gravar. |
| AP-09 | APIs deprecated/legadas | MEDIUM | Identificar dívida de compatibilidade com versão e documentação verificadas. |
| AP-10 | Erros dispersos ou inseguros | MEDIUM | Centralizar resposta sanitizada, propagação de erros e limpeza/rollback. |
| AP-11 | Nomes ambíguos | LOW | Explicitar o domínio preservando nomes públicos do contrato. |
| AP-12 | Valores mágicos ou código morto | LOW | Centralizar políticas e remover dependências sem consumidores. |
| AP-13 | Autenticação/autorização ausente | HIGH | Controlar identidade, papel e propriedade das operações sensíveis. |
| AP-14 | Escritas não atômicas/integridade quebrada | HIGH | Evitar pedidos, pagamentos, estoque e relações parcialmente gravados. |

### Como a skill permanece agnóstica de tecnologia

O fluxo se baseia em responsabilidades, entradas, persistência e contratos, sem fixar linguagem, framework, nomes de tabelas ou diretórios do domínio. As referências apresentam sinais e transformações para Python e JavaScript, mas selecionam as correções pela stack detectada. Views de APIs representam HTTP/JSON, sem exigir templates HTML. A injeção de dependências e os limites transacionais se adaptam tanto ao sqlite3 direto quanto ao SQLAlchemy.

A portabilidade foi exercitada copiando o mesmo pacote, sem diferenças de conteúdo, para os três projetos: dois Flask com níveis diferentes de organização e um Express. Isso comprova a reutilização nas stacks fornecidas; outras tecnologias ainda precisam de execução própria para serem consideradas validadas.

### Desafios e soluções

| Desafio encontrado | Solução adotada |
|---|---|
| Arquivos e linhas mudam durante a refatoração | Preservar auditoria do legado com commit-base/hashes; registrar correções e resultados em relatórios de validação separados. |
| Baseline aprovada não comprova o código novo | Manter o executor histórico separado e criar validações que iniciam os fontes correntes e exercitam todas as operações. |
| Segurança exige alterar comportamentos inseguros | Aprovar previamente autenticação, campos públicos e status 4xx, preservando os fluxos válidos e verificando recusas sem escrita. |
| Dados e senhas legadas devem continuar utilizáveis | Migração explícita e transacional no e-commerce Flask; migração MD5 após login válido no Task Manager; fixtures descartáveis sem alterar bancos locais. |
| Callbacks/erros assíncronos no Express | Encaminhar falhas à fronteira central e serializar unidades de trabalho com transação e rollback. |
| Task Manager já tinha pastas de camadas | Reaproveitar models/blueprints e extrair responsabilidades efetivas para controllers, repositories, serviços e views. |
| Nova revisão encontrou Unicode inválido produzindo 500 | Registrar C-01 separadamente, validar UTF-8 antes de hashing/persistência e acrescentar 56 casos HTTP. |
| Sandbox bloqueou sockets locais nas execuções | Executar os testes com permissão para loopback; tentativas bloqueadas não foram contadas como sucesso funcional. |

## Resultados

### Resumo das auditorias

| Projeto / auditoria do legado | Stack detectada | CRITICAL | HIGH | MEDIUM | LOW | Total | IDs manuais reconhecidos |
|---|---|---:|---:|---:|---:|---:|---:|
| [1 — E-commerce](reports/audit-project-1.md) | Python / Flask / sqlite3 | 3 | 5 | 2 | 1 | **11** | 5/5 |
| [2 — LMS](reports/audit-project-2.md) | JavaScript / Node.js / Express / sqlite3 | 2 | 3 | 3 | 2 | **10** | 5/5 |
| [3 — Task Manager](reports/audit-project-3.md) | Python / Flask / Flask-SQLAlchemy | 2 | 2 | 5 | 2 | **11** | 5/5 |
| **Total** | | **7** | **10** | **10** | **5** | **32** | **15/15** |

A [auditoria posterior do Task Manager](reports/audit-project-3-current.md) identificou **um MEDIUM adicional (C-01, Unicode inválido)**, corrigido e validado depois. Ele não integra os 32 findings históricos da tabela. Os relatórios de validação relacionam os findings às implementações e verificações; o texto de aprovação pendente nas auditorias registra o momento anterior à Fase 3.

### Estrutura antes/depois

As contagens incluem apenas arquivos de aplicação, excluindo testes, dependências, skill, caches e evidências. Linhas físicas incluem comentários e linhas vazias; o crescimento contempla camadas, configuração, segurança e integridade antes ausentes.

| Projeto | Antes: commit legado | Depois: código refatorado |
|---|---|---|
| E-commerce Flask | 4 arquivos Python / 780 linhas: `app.py`, `controllers.py`, `models.py`, `database.py`; HTTP, regras e SQL misturados. | 28 arquivos Python / 1.249 linhas: `app.py` e `src/{config,database,cli,errors,validation}.py`, `src/{models,services,controllers,views}/`. |
| LMS Express | 3 arquivos JS / 180 linhas: `src/{app,AppManager,utils}.js`; classe concentra roteamento, banco, checkout e relatório. | 16 arquivos JS / 547 linhas: `src/{app,config,database,seed,errors}.js`, `src/{models,controllers,services,views}/`; `AppManager.js` e `utils.js` removidos. |
| Task Manager Flask | 15 arquivos Python / 1.158 linhas: `app.py`, `database.py`, `seed.py`, `models/`, `routes/`, `services/`, `utils/`; regras e consultas nas rotas. | 35 arquivos Python / 1.322 linhas: mantém camadas úteis, acrescenta `config.py`, `errors.py`, `controllers/`, `views/`, repositories em `models/` e serviços de regras/autenticação. |

As árvores e responsabilidades completas estão nas validações dos [projetos 1](reports/validation-project-1.md#estrutura-e-responsabilidades), [2](reports/validation-project-2.md#estrutura-antesdepois) e [3](reports/validation-project-3.md#estrutura-mvc-verificada).

### Checklist de validação por projeto

**✅ = comprovado nos relatórios/fontes e evidências; N/A = verificado sem ocorrência aplicável.** Cada coluna corresponde à validação do respectivo projeto: [P1](reports/validation-project-1.md), [P2](reports/validation-project-2.md), [P3](reports/validation-project-3.md).

| Fase | Verificação | P1 — Flask loja | P2 — Express LMS | P3 — Flask tarefas |
|---|---|---|---|---|
| 1 | Linguagem detectada corretamente | ✅ Python | ✅ JavaScript | ✅ Python |
| 1 | Framework detectado corretamente | ✅ Flask | ✅ Express | ✅ Flask |
| 1 | Domínio descrito corretamente | ✅ E-commerce | ✅ LMS/checkout | ✅ Task Manager |
| 1 | Quantidade de fontes auditados e exclusões registradas | ✅ 4 | ✅ 3 | ✅ 15 |
| 2 | Relatório cobre os campos do template | ✅ | ✅ | ✅ |
| 2 | Findings com arquivos e linhas exatos do snapshot | ✅ | ✅ | ✅ |
| 2 | Ordenação CRITICAL → HIGH → MEDIUM → LOW | ✅ | ✅ | ✅ |
| 2 | Pelo menos cinco findings | ✅ 11 | ✅ 10 | ✅ 11 |
| 2 | Pelo menos cinco problemas da análise manual reconhecidos | ✅ 5/5 | ✅ 5/5 | ✅ 5/5 |
| 2 | Avaliação de APIs deprecated | N/A — sem ocorrência confirmada | N/A — sem ocorrência confirmada | ✅ `Query.get()` e `utcnow()` |
| 2 | Pausa e aprovação humana antes da Fase 3 | ✅ `sim` registrado | ✅ `sim` registrado | ✅ `sim` registrado |
| 3 | Diretórios/responsabilidades MVC | ✅ | ✅ | ✅ |
| 3 | Configuração em módulo próprio, sem segredos fixos | ✅ | ✅ | ✅ |
| 3 | Models abstraem dados/persistência | ✅ | ✅ | ✅ |
| 3 | Views/routes cuidam do transporte/apresentação | ✅ | ✅ | ✅ |
| 3 | Controllers coordenam o fluxo | ✅ | ✅ | ✅ |
| 3 | Tratamento de erros centralizado | ✅ | ✅ | ✅ |
| 3 | Entry point claro | ✅ `app.py` | ✅ `src/app.js` | ✅ `app.py` |
| 3 | Aplicação inicia sem erros | ✅ | ✅ | ✅ |
| 3 | Operações originais com fluxo de sucesso autorizado | ✅ 19/19 | ✅ 3/3 | ✅ 22/22 |

### Logs das aplicações após a refatoração

As evidências registram HTTP real em loopback, portas temporárias e bancos descartáveis. Os logs atendem ao requisito de comprovação de execução; os JSONs complementam com resultados, versões e hashes.

| Projeto | Resultado registrado | Evidências |
|---|---|---|
| P1 | **15/15 testes**, 155 verificações HTTP, 39 cenários históricos adaptados, zero falhas/erros. | [Log de boot/testes](reports/evidence/validation-project-1.log) · [JSON](reports/evidence/validation-project-1.json) |
| P2 | **34/34 cenários**, 3/3 operações; startup adicional por `npm start`, checkout 200 e relatório autorizado 200. | [Log de testes](reports/evidence/validation-project-2.log) · [Log de startup](reports/evidence/validation-project-2-boot.log) · [JSON](reports/evidence/validation-project-2.json) |
| P3 | **22/22 operações**, 313 resultados (291 HTTP + 22 invariantes), 1.136 verificações e zero desvios; lifecycle **21/21**. Inclui 56 casos Unicode/226 verificações. | [Log HTTP](reports/evidence/validation-project-3.log) · [JSON HTTP/boot](reports/evidence/validation-project-3.json) · [Log lifecycle](reports/evidence/validation-project-3-lifecycle.log) · [JSON lifecycle](reports/evidence/validation-project-3-lifecycle.json) |

Trechos das saídas registradas, com omissão de linhas intermediárias:

```text
# P1 — validation-project-1.log
 * Serving Flask app 'src'
 * Debug mode: off
 * Running on http://127.0.0.1:57147
Ran 15 tests in 8.502s
OK

# P2 — validation-project-2-boot.log
"command": "npm start"
"authorizedReport": 200
"anonymousReport": 401
"checkout": 200
"passed": true

# P3 — validation-project-3.log e validation-project-3-lifecycle.log
HTTP routes: 22/22; scenarios: 313; failures: 0
Lifecycle/CLI: 21 checks passed; local database untouched.
```

### Comportamento em stacks diferentes

No e-commerce Flask, a skill substituiu módulos misturados por uma factory e camadas por domínio, com SQL parametrizado, HTTP Basic, migração de senhas e transações de estoque/pedidos. No Express, preservou o framework e as dependências, extraiu o checkout da God Class e adaptou callbacks a erros centralizados e transações serializadas. No Task Manager, preservou a organização útil e o ORM, acrescentou repositories/controllers/views e verificou sessões, migração MD5, eager loading e APIs deprecated. Os casos mostram que o fluxo se adapta tanto à stack quanto ao grau de organização existente.

Os testes preservaram os bancos locais; notificações/pagamentos continuam simulados e o LMS mantém SQLite em memória. Não foram medidos cobertura de linhas ou testes de carga; o Task Manager não teve teste de concorrência. O sucesso dos cenários não representa garantia de ausência universal de defeitos.

### Verificação dos critérios de aceite

| Critério obrigatório | P1 | P2 | P3 | Situação |
|---|---|---|---|---|
| Fase 1 detecta a stack corretamente | Python/Flask | Node.js/Express | Python/Flask | **Atingido — 3/3** |
| Fase 2 encontra ≥ 5 findings | 11 | 10 | 11 | **Atingido — 3/3** |
| Fase 2 inclui ≥ 1 CRITICAL ou HIGH | 8 | 5 | 4 | **Atingido — 3/3** |
| Fase 3 funciona após refatoração: boot e todas as operações | 19/19 | 3/3 | 22/22 | **Atingido — 3/3** |

Os demais requisitos verificáveis localmente também estão atendidos: análise manual com a distribuição mínima, skill nos três projetos, cinco áreas de referência em Markdown, 14 anti-patterns com quatro severidades, detecção de deprecated, 14 transformações antes/depois, pausa humana documentada, três auditorias e logs após refatoração.

O histórico Git contém as refatorações de P1 (`06c8b2b`), P2 (`4245cdd`) e P3 (`7fa2776`). As afirmações de “sem commit” nos relatórios descrevem o momento de cada execução. **A visibilidade pública e a condição de fork no GitHub não foram verificadas nesta revisão local**; essa parte da entrega permanece sem comprovação aqui.

## Como Executar

### Pré-requisitos e preparação

Use **OpenAI Codex CLI instalado e autenticado**, com acesso ao modelo e às permissões necessárias para editar o projeto e executar testes HTTP em loopback. A instalação e autenticação estão na [documentação oficial do Codex CLI](https://learn.chatgpt.com/docs/codex/cli). A descoberta em `.agents/skills/` e a invocação com `$` seguem a [documentação oficial de skills](https://learn.chatgpt.com/docs/build-skills).

Também são necessários Git, Python com `venv`/pip e Node.js/npm. As validações registraram Python **3.14.4**, Node **24.19.0** e npm **11.17.0**. As dependências Python estão nos `requirements.txt`; o LMS usa `package-lock.json`. SQLite é utilizado localmente, sem servidor de banco externo.

Execute a partir da raiz do repositório:

```bash
codex --version
codex login

python3 -m venv code-smells-project/.venv
code-smells-project/.venv/bin/python -m pip install -r code-smells-project/requirements.txt

(cd ecommerce-api-legacy && npm ci)

python3 -m venv task-manager-api/.venv
task-manager-api/.venv/bin/python -m pip install -r task-manager-api/requirements.txt
```

As três cópias da skill já estão no repositório. Não é necessário instalar a skill globalmente. Inicie o Codex dentro do diretório de cada projeto para descobrir a cópia local.

### Executar a skill em cada projeto

Os comandos abaixo iniciam sessões interativas separadas, partindo da raiz. As aspas simples preservam o `$refactor-arch` no prompt. Os nomes de reauditoria evitam sobrescrever as evidências históricas:

```bash
# P1 — Python/Flask, E-commerce
(cd code-smells-project && codex '$refactor-arch Analise e audite este projeto. Proponha ../reports/audit-project-1-reauditoria.md e aguarde aprovação antes da Fase 3.')

# P2 — Node.js/Express, LMS
(cd ecommerce-api-legacy && codex '$refactor-arch Analise e audite este projeto. Proponha ../reports/audit-project-2-reauditoria.md e aguarde aprovação antes da Fase 3.')

# P3 — Python/Flask, Task Manager
(cd task-manager-api && codex '$refactor-arch Analise e audite este projeto. Proponha ../reports/audit-project-3-reauditoria.md e aguarde aprovação antes da Fase 3.')
```

Revise o resumo da stack, o inventário, os findings e o plano apresentados. Responda `sim` somente após revisar o relatório para autorizar seu salvamento e a Fase 3. O código atual já está refatorado: uma nova auditoria pode encontrar menos problemas que a auditoria do legado, sem invalidar os números históricos nem justificar findings artificiais.

### Validar a refatoração

Partindo da raiz, execute os runners dos **fontes correntes**. As saídas de uma nova execução ficam em um diretório temporário para preservar as evidências entregues:

```bash
validation_dir="$(mktemp -d)"

(cd code-smells-project && .venv/bin/python tests/run_validation.py) \
  > "$validation_dir/validation-project-1.json" 2> "$validation_dir/validation-project-1.log"

(cd ecommerce-api-legacy && npm test -- --json "$validation_dir/validation-project-2.json") \
  > "$validation_dir/validation-project-2.log" 2>&1

(cd task-manager-api && .venv/bin/python -B tests/run_validation.py \
  --output "$validation_dir/validation-project-3.json") \
  > "$validation_dir/validation-project-3.log" 2>&1

(cd task-manager-api && .venv/bin/python -B tests/check_lifecycle.py \
  --output "$validation_dir/validation-project-3-lifecycle.json") \
  > "$validation_dir/validation-project-3-lifecycle.log" 2>&1

printf 'Evidências desta execução: %s\n' "$validation_dir"
```

Cada comando deve terminar com **código 0**, sem falhas, com boot confirmado e **19/19, 3/3 e 22/22 operações**, respectivamente; lifecycle deve informar **21 verificações aprovadas**. Confira também os cenários de autorização, validação, rollback, persistência, ausência de dados sensíveis e consultas em lote descritos nas validações. Os runners usam bancos descartáveis e não exigem seed ou migração dos bancos locais.

Para iniciar manualmente, preparar um banco novo, migrar o banco legado ou provisionar usuários, consulte os READMEs de [P1](code-smells-project/README.md#preparar-e-executar), [P2](ecommerce-api-legacy/README.md#como-executar) e [P3](task-manager-api/README.md#preparação-e-execução). Os dois Flask usam porta 5000 por padrão: execute separadamente ou configure `PORT`. Autenticação e permissões estão documentadas em cada projeto.

O comando `python3 scripts/baseline/run.py` serve exclusivamente para reproduzir o **commit legado**, conforme os [relatórios de baseline](reports/). Ele não valida a refatoração atual.

---

# Enunciado original — Criação de Skills: Refatoração Arquitetural Automatizada

> O conteúdo abaixo preserva os requisitos e exemplos do desafio. O estado efetivamente entregue está documentado nas seções acima.

Ao longo do curso você aprendeu o que são Skills e como elas permitem que um agente de IA atue como um especialista em tarefas específicas. Agora imagine o seguinte cenário: você herdou 3 projetos legados com problemas de arquitetura, segurança e qualidade de código. Revisar e corrigir tudo manualmente levaria dias.

Neste desafio, você vai criar uma Skill que automatiza esse processo — analisando, auditando e refatorando qualquer projeto para o padrão MVC, independente da tecnologia.

## Commit-base do código legado

O commit `6d1ce6248c3e956801010a89d8bdaab48029bf30` registra o código legado dos três projetos deste repositório: `code-smells-project/`, `ecommerce-api-legacy/` e `task-manager-api/`.

Use esse mesmo hash no campo `commit-base` dos três relatórios de auditoria. Os arquivos e as linhas de cada finding devem corresponder ao código desse commit, anterior à refatoração.

## Baseline funcional do legado

A baseline foi executada sobre cópias temporárias do commit-base, com servidores HTTP reais em `127.0.0.1`, portas temporárias e bancos descartáveis. Os fontes das aplicações e os dois bancos locais existentes foram preservados.

| Projeto | Relatório | Operações exercitadas | Cenários | Cenários com desvios |
|---|---|---|---|---|
| Python/Flask — E-commerce | [Baseline do projeto 1](reports/baseline-project-1.md) | 19/19 | 39 | 12 |
| Node.js/Express — LMS | [Baseline do projeto 2](reports/baseline-project-2.md) | 3/3 | 14 | 6 |
| Python/Flask — Task Manager | [Baseline do projeto 3](reports/baseline-project-3.md) | 22/22 | 57 | 12 |
| **Total** | | **44/44** | **110** | **30** |

Os desvios incluem entradas inválidas que retornam 500, exposição de senhas/configuração, falhas de autorização e integridade referencial. No LMS, um campo `card` numérico encerrou o processo com código 1, sem resposta HTTP. As expectativas dos cenários indicam o comportamento correto desejado; os defeitos observados devem ser corrigidos na refatoração.

Cada relatório referencia o JSON de requisições, respostas sanitizadas, verificações e efeitos no banco, além do log de boot e erros. Esses registros estão em [reports/evidence/](reports/evidence/). Eles documentam a baseline anterior à refatoração; as auditorias da Fase 2 estão disponíveis em [audit-project-1.md](reports/audit-project-1.md), [audit-project-2.md](reports/audit-project-2.md) e [audit-project-3.md](reports/audit-project-3.md).

Para reproduzir, com os ambientes locais preparados conforme o [plano de execução](PLANO_EXECUCAO.md#4-execute-os-legados-e-registre-uma-baseline):

```bash
python3 scripts/baseline/run.py
# Executar somente um projeto:
python3 scripts/baseline/run.py --project 2
```

O executor usa os fontes do commit-base registrado, reutiliza `.venv` de cada Flask e `node_modules` do LMS e recria os dados apenas nas cópias temporárias. A cobertura indica combinações de método e rota exercitadas, sem representar cobertura completa de linhas ou de entradas possíveis.

## Objetivo

Você deve entregar uma Skill capaz de:

- Analisar uma codebase detectando linguagem, framework e arquitetura atual
- Identificar anti-patterns e code smells, classificando por severidade com arquivo e linha exatos
- Gerar um relatório de auditoria estruturado com todos os achados
- Refatorar o projeto para o padrão MVC (Model-View-Controller), eliminando os problemas encontrados
- Validar o resultado garantindo que a aplicação continua funcionando após as mudanças

A skill deve ser agnóstica de tecnologia, funcionando com diferentes linguagens e frameworks.

## Contexto

### Definição de Severidades

Para padronizar a sua auditoria e os relatórios gerados pela IA, utilize a seguinte escala de classificação baseada em problemas de MVC e SOLID:

- **CRITICAL:** Falhas graves de arquitetura ou segurança que impedem o funcionamento correto, expõem dados sensíveis (ex: credenciais hardcoded, SQL Injection) ou violam completamente a separação de responsabilidades (ex: "God Class" contendo banco de dados, lógicas complexas e roteamento no mesmo arquivo).
- **HIGH:** Fortes violações do padrão MVC ou princípios SOLID que dificultam muito a manutenção e testes (ex: lógicas de negócio pesadas presas dentro de Controllers, forte acoplamento sem Injeção de Dependência, ou uso de estado global mutável em toda a aplicação).
- **MEDIUM:** Problemas de padronização, duplicação de código ou gargalos de performance moderada (ex: Queries N+1 no banco de dados, uso inadequado de middlewares, validações ausentes nas rotas).
- **LOW:** Melhorias de legibilidade, nomenclatura de variáveis ruins, ou "magic numbers" soltos pelo código.

### Exemplo de Uso no CLI

```bash
# Executar a skill no projeto com problemas
cd code-smells-project
claude "/refactor-arch"
```

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python
Framework:      Flask 3.1.1
Dependencies:  flask-cors
Domain:        E-commerce API (produtos, pedidos, usuários)
Architecture:  Monolítica — tudo em 4 arquivos, sem separação de camadas
Source files:  4 files analyzed
DB tables:     produtos, usuarios, pedidos, itens_pedido
================================
```

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask
Files:   4 analyzed | ~800 lines of code

## Summary
CRITICAL: 4 | HIGH: 5 | MEDIUM: 2 | LOW: 3

## Findings

### [CRITICAL] God Class / God Method
File: models.py:1-350
Description: Arquivo único contém toda lógica de negócio, queries SQL, validação e formatação para 4 domínios diferentes.
Impact: Impossível testar em isolamento, qualquer mudança afeta tudo.
Recommendation: Separar em models e controllers por domínio.

### [CRITICAL] Hardcoded Credentials
File: app.py:8
Description: SECRET_KEY hardcoded como 'minha-chave-super-secreta-123'
...

================================
Total: 14 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
> y
```

```
[... refatoração executada ...]

================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
src/
├── config/settings.py
├── models/
│   ├── produto_model.py
│   └── usuario_model.py
├── views/
│   └── routes.py
├── controllers/
│   ├── produto_controller.py
│   └── pedido_controller.py
├── middlewares/error_handler.py
└── app.py (composition root)

## Validation
  ✓ Application boots without errors
  ✓ All endpoints respond correctly
  ✓ Zero anti-patterns remaining
================================
```

## Tecnologias obrigatórias

- **Ferramenta:** uma das três opções abaixo (não são aceitas outras ferramentas):
  - Claude Code
  - Gemini CLI
  - OpenAI Codex
- **Recurso:** Custom Skills (ou o equivalente na ferramenta escolhida)
- **Formato dos arquivos de referência:** Markdown
- **Projetos-alvo:** Python/Flask (2 projetos) e Node.js/Express (1 projeto) (fornecidos no repositório base)

> **Nota sobre a ferramenta:** Os exemplos deste documento usam o Claude Code (`.claude/skills/`) como referência, pois é a ferramenta utilizada no curso. Se você optar por Gemini CLI ou Codex, adapte o nome da pasta e o comando de invocação conforme a convenção dela — o conceito de skill e a estrutura interna (SKILL.md + arquivos de referência) permanecem os mesmos.

## Requisitos

### 1. Análise Manual dos Projetos

Antes de criar a skill, você deve entender os problemas que ela vai resolver.

**Tarefas:**

- Analisar o projeto `code-smells-project/` (Python/Flask — API de E-commerce)
- Analisar o projeto `ecommerce-api-legacy/` (Node.js/Express — LMS API com fluxo de checkout)
- Analisar o projeto `task-manager-api/` (Python/Flask — API de Task Manager)

Para cada projeto, identificar e documentar no mínimo 5 problemas, incluindo pelo menos:

- 1 de severidade CRITICAL ou HIGH
- 2 de severidade MEDIUM
- 2 de severidade LOW

Documentar os achados na seção "Análise Manual" do seu `README.md`

> **Dica:** Não precisa encontrar todos os problemas — foque nos que têm maior impacto arquitetural. Use os projetos como insumo para entender quais padrões sua skill precisa detectar.

> **Por que 3 projetos?** Dois são Python/Flask (com níveis de organização diferentes) e um é Node.js/Express. Sua skill precisa funcionar nos 3 para provar que é verdadeiramente agnóstica de tecnologia — lidando tanto com código completamente desestruturado quanto com projetos que já possuem alguma separação de camadas.

### 2. Criação da Skill

Agora que você conhece os problemas, crie uma skill que os detecte, gere um relatório de auditoria e corrija automaticamente.

**Tarefas:**

Criar a skill dentro do projeto `code-smells-project/` e implementar o SKILL.md com 3 fases sequenciais:

- **Fase 1 — Análise:** Detectar stack, mapear arquitetura atual, imprimir resumo
- **Fase 2 — Auditoria:** Cruzar código contra catálogo de anti-patterns, gerar relatório, pedir confirmação
- **Fase 3 — Refatoração:** Reestruturar para o padrão MVC, validar que funciona

Criar arquivos de referência em Markdown que forneçam à skill o conhecimento necessário para executar as 3 fases. Os arquivos devem cobrir **obrigatoriamente** as seguintes áreas de conhecimento:

| Área de conhecimento | O que deve conter |
|---|---|
| Análise de projeto | Heurísticas para detecção de linguagem, framework, banco de dados e mapeamento de arquitetura |
| Catálogo de anti-patterns | Anti-patterns com sinais de detecção e classificação de severidade |
| Template de relatório | Formato padronizado do relatório de auditoria (Fase 2) |
| Guidelines de arquitetura | Regras do padrão MVC alvo (camadas Models, Views/Routes e Controllers, responsabilidades de cada uma) |
| Playbook de refatoração | Padrões concretos de transformação para cada anti-pattern (com exemplos de código) |

> **Nota:** Você tem liberdade para organizar os arquivos de referência como preferir — pode usar os nomes e a quantidade de arquivos que fizer sentido para sua skill. O importante é que todas as 5 áreas de conhecimento estejam cobertas. O nome da skill (`refactor-arch`) e o arquivo `SKILL.md` são obrigatórios e não devem ser alterados. O path da skill segue a convenção da ferramenta escolhida (no Claude Code, por exemplo, é `.claude/skills/refactor-arch/`).

**Requisitos da skill:**

- Deve ser agnóstica de tecnologia — deve funcionar corretamente nos 3 projetos fornecidos, independente da stack ou nível de organização
- O catálogo de anti-patterns deve conter no mínimo 8 anti-patterns com severidade distribuída (CRITICAL, HIGH, MEDIUM, LOW)
- O catálogo deve incluir detecção de APIs deprecated — identificar uso de APIs obsoletas e recomendar o equivalente moderno
- O playbook deve ter no mínimo 8 padrões de transformação com exemplos de código antes/depois
- A Fase 2 deve pausar e pedir confirmação antes de modificar qualquer arquivo
- A Fase 3 deve validar o resultado (boot da aplicação + endpoints funcionando)

### 3. Execução da Skill

Execute sua skill nos 3 projetos e valide que ela funciona em todas as stacks.

#### Projeto 1 — code-smells-project (Python/Flask)

Invocar a skill no Claude Code:

```bash
claude "/refactor-arch"
```

> **Nota:** O comando acima é o exemplo com Claude Code. Se você estiver usando Gemini CLI ou Codex, utilize o comando equivalente para invocar uma skill na sua ferramenta.

- Verificar que a Fase 1 detecta corretamente a stack e imprime o resumo
- Verificar que a Fase 2 encontra no mínimo 5 dos problemas documentados na sua análise manual
- Confirmar a execução da Fase 3
- Verificar que a Fase 3:
  - Cria a estrutura de diretórios baseada em MVC
  - A aplicação inicia sem erros
  - Os endpoints originais continuam respondendo
- Salvar o relatório de auditoria (output da Fase 2) em `reports/audit-project-1.md`
- Commitar o código refatorado do projeto no repositório

#### Projeto 2 — ecommerce-api-legacy (Node.js/Express)

Prove que sua skill é reutilizável em outro projeto de backend, mas com stack diferente.

- Copiar a pasta `.claude/skills/refactor-arch/` para dentro de `ecommerce-api-legacy/`
- Invocar a skill:

```bash
cd ../ecommerce-api-legacy
claude "/refactor-arch"
```

- Verificar que as 3 fases executam corretamente neste projeto
- Salvar o relatório em `reports/audit-project-2.md`
- Commitar o código refatorado do projeto no repositório

#### Projeto 3 — task-manager-api (Python/Flask)

Agora o teste com um projeto Python/Flask que já possui alguma organização de camadas (models, routes, services, utils).

- Copiar a pasta `.claude/skills/refactor-arch/` para dentro de `task-manager-api/`
- Invocar a skill:

```bash
cd ../task-manager-api
claude "/refactor-arch"
```

- Verificar que:
  - A Fase 1 detecta corretamente Python/Flask como stack e identifica o domínio de Task Manager
  - A Fase 2 identifica problemas mesmo em um projeto parcialmente organizado
  - A Fase 3 melhora a estrutura sem quebrar a aplicação (todos os endpoints devem continuar respondendo)
- Salvar o relatório em `reports/audit-project-3.md`
- Commitar o código refatorado do projeto no repositório

> **Nota:** Este projeto já possui alguma separação de camadas, mas isso não significa que a arquitetura está adequada. A skill deve identificar tanto problemas de código (segurança, performance, qualidade) quanto oportunidades de melhoria arquitetural. Se houver mudanças estruturais necessárias, a skill deve propô-las e executá-las.

#### Validação

Para cada projeto refatorado, valide o seguinte checklist:

```markdown
## Checklist de Validação

### Fase 1 — Análise
- [ ] Linguagem detectada corretamente
- [ ] Framework detectado corretamente
- [ ] Domínio da aplicação descrito corretamente
- [ ] Número de arquivos analisados condiz com a realidade

### Fase 2 — Auditoria
- [ ] Relatório segue o template definido nos arquivos de referência
- [ ] Cada finding tem arquivo e linhas exatos
- [ ] Findings ordenados por severidade (CRITICAL → LOW)
- [ ] Mínimo de 5 findings identificados
- [ ] Detecção de APIs deprecated incluída (se aplicável)
- [ ] Skill pausa e pede confirmação antes da Fase 3

### Fase 3 — Refatoração
- [ ] Estrutura de diretórios segue padrão MVC
- [ ] Configuração extraída para módulo de config (sem hardcoded)
- [ ] Models criados para abstrair dados
- [ ] Views/Routes separadas para visualização ou roteamento
- [ ] Controllers concentram o fluxo da aplicação
- [ ] Error handling centralizado
- [ ] Entry point claro
- [ ] Aplicação inicia sem erros
- [ ] Endpoints originais respondem corretamente
```

> **Dica:** Se a skill não detectou problemas suficientes ou a refatoração falhou, ajuste os arquivos de referência e execute novamente. É normal precisar de 2-4 iterações.

## Entregável

Repositório público no GitHub (fork do repositório base) contendo:

- Skill completa em `.claude/skills/refactor-arch/` (dentro dos 3 projetos)
- Código refatorado dos 3 projetos (resultado da execução da Fase 3, commitado no repositório)
- Relatórios de auditoria em `reports/` (3 arquivos)
- `README.md` atualizado

### Estrutura do repositório

Faça um fork do repositório base contendo os três projetos com code smells.

> **Nota:** A estrutura abaixo usa Claude Code como exemplo (`.claude/skills/`). Se estiver usando outra ferramenta, adapte os caminhos conforme a convenção dela.

```
desafio-skills/
├── README.md                              # Sua documentação
│
├── code-smells-project/                   # Projeto 1 — Python/Flask (API de E-commerce)
│   ├── .claude/
│   │   └── skills/
│   │       └── refactor-arch/             # ← SUA SKILL AQUI
│   │           ├── SKILL.md
│   │           └── (arquivos de referência)
│   ├── app.py
│   ├── controllers.py
│   ├── models.py
│   ├── database.py
│   └── requirements.txt
│
├── ecommerce-api-legacy/                  # Projeto 2 — Node.js/Express (LMS API com checkout)
│   ├── .claude/
│   │   └── skills/
│   │       └── refactor-arch/             # ← CÓPIA DA SKILL
│   │           └── ...
│   ├── src/
│   │   ├── app.js
│   │   ├── AppManager.js
│   │   └── utils.js
│   ├── api.http
│   └── package.json
│
├── task-manager-api/                      # Projeto 3 — Python/Flask (API de Task Manager)
│   ├── .claude/
│   │   └── skills/
│   │       └── refactor-arch/             # ← CÓPIA DA SKILL
│   │           └── ...
│   ├── app.py
│   ├── database.py
│   ├── seed.py
│   ├── requirements.txt
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── utils/
│
└── reports/                               # Relatórios gerados
    ├── audit-project-1.md                 # Saída da Fase 2 no projeto 1
    ├── audit-project-2.md                 # Saída da Fase 2 no projeto 2
    └── audit-project-3.md                 # Saída da Fase 2 no projeto 3
```

**O que você vai criar:**

- `.claude/skills/refactor-arch/` — A skill completa (SKILL.md + arquivos de referência)
- Código refatorado dos 3 projetos — resultado da execução da Fase 3, commitado no repositório
- `reports/audit-project-{1,2,3}.md` — Relatório de auditoria de cada projeto
- `README.md` — Documentação do seu processo

**O que já vem pronto:**

- `code-smells-project/` — API de E-commerce Python/Flask com code smells intencionais
- `ecommerce-api-legacy/` — LMS API Node.js/Express (com fluxo de checkout) e problemas de implementação
- `task-manager-api/` — API de Task Manager Python/Flask com organização parcial e problemas de segurança/qualidade

> **Dica:** Cada projeto contém problemas intencionais de diferentes severidades (CRITICAL, HIGH, MEDIUM, LOW), incluindo falhas de segurança, violações arquiteturais e problemas de qualidade de código. Parte do desafio é identificá-los por conta própria através da análise manual do código.

### README.md deve conter

**A) Seção "Análise Manual":**

- Lista dos problemas identificados manualmente em cada projeto
- Classificação por severidade
- Justificativa de por que cada problema é relevante

**B) Seção "Construção da Skill":**

- Decisões de design: como estruturou o SKILL.md e os arquivos de referência
- Quais anti-patterns incluiu no catálogo e por quê
- Como garantiu que a skill é agnóstica de tecnologia
- Desafios encontrados e como resolveu

**C) Seção "Resultados":**

- Resumo dos relatórios de auditoria dos 3 projetos (quantos findings por severidade em cada)
- Comparação antes/depois da estrutura de cada projeto
- Checklist de validação preenchido para cada projeto
- Screenshots ou logs mostrando as aplicações rodando após refatoração
- Observações sobre como a skill se comportou em stacks diferentes

**D) Seção "Como Executar":**

- Pré-requisitos (a ferramenta escolhida — Claude Code, Gemini CLI ou Codex — instalada e configurada)
- Comandos para executar a skill em cada projeto
- Como validar que a refatoração funcionou

### Ordem de execução sugerida

**1. Analisar os projetos manualmente**

Leia o código dos três projetos e documente os problemas encontrados.

**2. Criar a skill**

Escreva o SKILL.md e os arquivos de referência.

**3. Executar nos 3 projetos**

```bash
# Projeto 1
cd code-smells-project
claude "/refactor-arch"

# Projeto 2
cd ../ecommerce-api-legacy
claude "/refactor-arch"

# Projeto 3
cd ../task-manager-api
claude "/refactor-arch"
```

Salve a saída da Fase 2 de cada projeto em `reports/audit-project-{1,2,3}.md`.

**4. Iterar**

Se a skill não detectou problemas suficientes ou a refatoração falhou, ajuste os arquivos de referência e execute novamente. É normal precisar de 2-4 iterações.

## Critérios de Aceite

A skill deve atingir os seguintes mínimos em **todos os 3 projetos**:

| Critério | Requisito |
|---|---|
| Fase 1 detecta stack corretamente | OBRIGATÓRIO (3/3 projetos) |
| Fase 2 encontra >= 5 findings | OBRIGATÓRIO (3/3 projetos) |
| Fase 2 inclui pelo menos 1 CRITICAL ou HIGH | OBRIGATÓRIO (3/3 projetos) |
| Fase 3 aplicação funciona após refatoração | OBRIGATÓRIO (3/3 projetos) |

**IMPORTANTE:** Todos os critérios devem ser atingidos nos 3 projetos, não apenas em um!

> **Sobre o projeto 3 (task-manager-api):** Este projeto já possui alguma organização. "aplicação funciona" significa que a API inicia sem erros e todos os endpoints continuam respondendo corretamente.

## Referências

- [Claude Code: Skills](https://docs.anthropic.com/en/docs/claude-code/skills) — Documentação oficial sobre como criar e estruturar Skills
- [Claude Code: Overview](https://docs.anthropic.com/en/docs/claude-code/overview) — Visão geral do Claude Code e suas capacidades
- [The Complete Guide to Building Skills for Claude (PDF)](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf) — Guia completo da Anthropic sobre construção de Skills
- [Equipping Agents for the Real World with Agent Skills](https://claude.com/blog/equipping-agents-for-the-real-world-with-agent-skills) — Blog oficial da Anthropic sobre Agent Skills

---

## Dicas Finais

- **Comece pela análise manual** — entender os problemas profundamente é essencial para criar uma skill que os detecte.
- **O SKILL.md é um prompt** — ele instrui o agente sobre o que fazer, enquanto os arquivos de referência fornecem o conhecimento de domínio.
- **Seja específico nos sinais de detecção** — "código ruim" não ajuda; "query SQL dentro de loop for" é acionável.
- **Teste incrementalmente** — não tente criar a skill perfeita de primeira.
- **A skill deve ser copiável** — se ela só funciona em um projeto específico, está acoplada demais. Teste nos 3 projetos para validar.
- **Projetos diferentes exigem adaptação** — a Fase 3 de um projeto já parcialmente organizado não vai ter as mesmas transformações de um monolito. Sua skill deve se adaptar ao contexto.
- **Pedir confirmação na Fase 2 é obrigatório** — o humano deve revisar o relatório antes de qualquer modificação.
- **Consulte as referências do curso** — revise a documentação oficial da ferramenta escolhida e os materiais das aulas para relembrar a estrutura e anatomia de uma skill.
