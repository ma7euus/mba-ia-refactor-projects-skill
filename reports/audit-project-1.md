Executei as Fases 1 e 2 da `refactor-arch` em modo somente leitura. A auditoria encontrou **11 problemas: 3 CRITICAL, 5 HIGH, 2 MEDIUM e 1 LOW**. A Fase 3 aguarda sua aprovação, conforme o passo a passo.

## Relatório de auditoria — `code-smells-project`

### Estado auditado

- **Aplicação:** `code-smells-project/`.
- **Repositório:** `/home/mateus/projetos/mateus/mba/mba-ia-refactor-projects-skill`.
- **HEAD:** `7ddd47686a1fc6c6be968b9adf9789ee18ae3ce5`.
- **Commit-base:** `6d1ce6248c3e956801010a89d8bdaab48029bf30`. Conferi que os quatro fontes Python e `requirements.txt` continuam iguais aos desse commit.
- **Alterações locais existentes:** `SKILL.md` e as referências `anti-patterns.md`, `mvc-guidelines.md`, `project-analysis.md` e `refactoring-playbook.md`. Nenhuma alteração nos fontes da aplicação.
- **Data:** 30/10/2026, 21:59, America/Sao_Paulo.
- **Ferramenta:** Codex; identificador exato do modelo indisponível.
- **Destino proposto:** `reports/audit-project-1.md`, na raiz do repositório, conforme o passo a passo.

SHA-256 dos fontes inspecionados:

```text
app.py
2ce0981b36199939d2100e8d788a6081637e70932e07abf61da309bfb655323c
controllers.py
41542c293ad5b21dbcb6cb1154d068dbe35aad55e6879f6fb7fc0d72217b1b4f
database.py
cb15ddec38ed506fd2655960deb4f8cad5b830846cd5e987fb28a6c633bf8707
models.py
6832a37cc4fe8632c40b5580bb3e835bc9eafc0ab1ba4249c016fbe0e7fe9345
```

### Fase 1 — Análise do projeto

| Campo | Resultado e evidência |
|---|---|
| Linguagem e runtime | Python; ambiente local informa **3.14.4**. |
| Framework | **Flask 3.1.1** e **flask-cors 5.0.1**, declarados em `requirements.txt` e confirmados pelos metadados da `.venv`. Werkzeug instalado: **3.1.9**. Não há lockfile Python. |
| Domínio | Loja: produtos, usuários, pedidos, estoque e relatório de vendas. |
| Persistência | SQLite via `sqlite3`; quatro tabelas: `produtos`, `usuarios`, `pedidos` e `itens_pedido`. |
| Banco | `loja.db`, relativo ao diretório de execução. Existe um banco local, cujo conteúdo não foi consultado nesta fase. |
| Inicialização | `get_db()` cria tabelas e popula dados de exemplo quando não há produtos. O boot executa essa função. |
| Entrada | `app.py`; comando atual: `.venv/bin/python app.py`, dentro do projeto. |
| Arquitetura | Separação inicial entre rotas, controllers e models, com regras de negócio, SQL, configuração e apresentação atravessando essas fronteiras. |
| Inventário | **4 arquivos Python, 780 linhas físicas**, incluindo comentários e linhas vazias; **19 operações HTTP explícitas**. |
| Exclusões | `.agents`, `.venv`, caches, banco, documentação, evidências, dependências e rotas automáticas HEAD/OPTIONS/static. |
| Integrações | Email, SMS e push são apenas mensagens no console. |
| Evidência funcional | [Baseline existente](baseline-project-1.md): 19/19 operações, 39 cenários e 12 cenários com desvios. |

A baseline foi executada em **30/10/2026, às 02:09:49 UTC**, sobre cópia isolada do commit-base. Seus resultados são históricos. **Não iniciei a aplicação, importei seus módulos, instalei dependências ou executei requisições nesta auditoria.**

### Fase 2 — Achados

| CRITICAL | HIGH | MEDIUM | LOW | Total |
|---:|---:|---:|---:|---:|
| 3 | 5 | 2 | 1 | **11** |

Os caminhos e intervalos abaixo são relativos a `code-smells-project/`. Nenhum valor de senha ou segredo foi reproduzido.

#### F-01 — CRITICAL — SQL construído com entrada do cliente

- **Catálogo:** AP-01.
- **Locais:** `controllers.py:167–176` → `models.py:105–111`; outras ocorrências em `models.py:43–61`, `122–129` e `285–299`.
- **Evidência:** email, senha, campos de produtos e filtros são concatenados no texto entregue a `cursor.execute()`.
- **Impacto e classificação:** entradas controlam a estrutura SQL, permitindo alteração da consulta e potencial desvio de autenticação. Os IDs convertidos pelo roteador não são a base dessa conclusão.
- **Confirmação:** análise estática; o cenário histórico **P1-20 da baseline** também demonstrou erro SQL com um nome comum contendo apóstrofo. Não executei ataques.
- **Correção e compatibilidade:** parametrizar valores, preservando os campos públicos e aceitando apóstrofos como dados.
- **Validação:** login correto/incorreto, cadastro e busca com apóstrofos e entradas que devem permanecer valores literais.

#### F-02 — CRITICAL — Senhas e segredo expostos em respostas

- **Catálogo:** AP-02.
- **Locais:** `models.py:72–103` → `controllers.py:128–144`; `app.py:7` e `controllers.py:285–290`.
- **Evidência:** listagem/detalhe de usuário incluem `senha`; `/health` devolve `secret_key`.
- **Impacto e classificação:** exposição direta de credenciais e configuração sensível por operações HTTP comuns.
- **Confirmação:** estática e cenários históricos P1-02, P1-08 e P1-09 da baseline.
- **Correção e compatibilidade:** serializers com campos públicos explícitos; retirar senha, hashes e segredo dos payloads. Remover o segredo fixo e desativar debug por padrão.
- **Validação:** percorrer respostas e erros, verificando ausência desses campos e valores.

#### F-03 — CRITICAL — Operações sensíveis sem autorização

- **Catálogo:** AP-13.
- **Locais:** `app.py:11–30`, `47–78`; `controllers.py:167–183`.
- **Evidência:** `/admin/query` executa SQL recebido e `/admin/reset-db` apaga quatro tabelas sem verificar identidade. O login apenas devolve dados; não autentica requisições seguintes.
- **Impacto e classificação:** leitura arbitrária e exclusão integral sem autorização. A baseline confirmou consulta anônima e reset efetivo em banco descartável.
- **Correção e compatibilidade:** estabelecer autenticação verificável, conferir papel/propriedade e manter as duas rotas administrativas com operações limitadas. Haverá mudança intencional para `401/403` nos acessos indevidos.
- **Validação:** acesso anônimo, cliente, proprietário e administrador; negativas devem preservar os dados.

#### F-04 — HIGH — Armazenamento de senha em texto puro

- **Catálogo:** AP-05.
- **Locais:** `models.py:105–111`, `122–130`; `database.py:75–83`.
- **Evidência:** cadastro grava a senha recebida; login compara diretamente no SQL. Há credenciais de demonstração fixas no seed.
- **Impacto e classificação:** acesso ao banco revela imediatamente as senhas. O cenário histórico P1-11 confirmou armazenamento textual.
- **Correção e compatibilidade:** hash adaptativo com Werkzeug, verificação apropriada e migração explícita dos registros existentes, preservando IDs e relações.
- **Validação:** senha anterior continua funcionando para usuário migrado, senha errada falha, cadastro novo armazena hash e repetir a migração não altera novamente o hash.

#### F-05 — HIGH — Conexão SQLite global sem ciclo de vida controlado

- **Catálogo:** AP-06.
- **Locais:** `database.py:4–12`, `84–86`; consumidores em models e rotas administrativas.
- **Evidência:** uma conexão global com `check_same_thread=False` atende os fluxos, sem fechamento ou rollback por requisição.
- **Impacto e classificação:** compartilhamento de estado transacional entre requisições e dificuldade de isolamento.
- **Limite:** o risco decorre do fluxo estático; não foi medido sob concorrência.
- **Correção e compatibilidade:** conexão por contexto de requisição, configuração injetada, fechamento e rollback definidos.
- **Validação:** falha seguida de operação válida, isolamento entre requisições e disputa controlada pelo estoque.

#### F-06 — HIGH — Integridade relacional e transacional insuficiente

- **Catálogo:** AP-14.
- **Locais:** `models.py:65–70`, `133–169`; `database.py:36–53`.
- **Evidência:** criação de pedido não verifica usuário; esquema não declara chaves estrangeiras; exclusão de produto ignora itens históricos.
- **Impacto e classificação:** pedidos e itens podem ficar órfãos. A baseline P1-33 confirmou pedido para usuário inexistente.
- **Contexto:** a criação já possui um único commit ao final; não há evidência de commits independentes. A ausência de rollback exige teste específico.
- **Correção e compatibilidade:** validar vínculos, transação explícita e impedir exclusão de produto referenciado com `409`. Usuário inexistente passará a `404`.
- **Validação:** vínculos válidos/inválidos, falha intermediária sem gravação parcial e exclusão de produto referenciado.

#### F-07 — HIGH — Validação permite estoque e totais inválidos

- **Catálogo:** AP-08.
- **Locais:** `controllers.py:37–50`, `81–90`, `113–126`, `188–203`, `237–252`; `models.py:139–166`, `275–283`.
- **Evidência:** quantidade negativa passa pela comparação de estoque e aumenta o saldo; produtos repetidos são validados separadamente. Conversões numéricas não são protegidas. Atualização de status não verifica pedido inexistente.
- **Impacto e classificação:** corrupção demonstrada de estoque e total financeiro. A baseline confirmou quantidade negativa, erros de tipos e falso sucesso ao atualizar pedido inexistente.
- **Correção e compatibilidade:** validar tipos, finitude, faixas e quantidades inteiras positivas; agregar quantidades por produto; conferir existência e linhas atualizadas.
- **Validação:** entradas inválidas retornam `400` sem mutação; pedido inexistente retorna `404`; soma dos itens corresponde ao total e à baixa do estoque.

#### F-08 — HIGH — Responsabilidades atravessam as camadas

- **Catálogo:** AP-04.
- **Locais:** `controllers.py:24–58`, `64–93`, `188–216`, `237–252`, `264–289`; `app.py:47–78`; `models.py:235–272`.
- **Evidência:** controllers contêm regras de produto, notificações e SQL; rotas administrativas executam persistência; o model de relatório calcula política comercial.
- **Impacto e classificação:** forte acoplamento entre HTTP, regras de negócio e armazenamento dificulta testes e alterações isoladas.
- **Contexto:** a separação existente será aproveitada. Não contei um achado adicional de “God Module” sobre essas mesmas ocorrências.
- **Correção e compatibilidade:** controllers coordenam casos de uso; models/repositórios cuidam dos dados; serviços concentram pedidos e relatórios; views serializam JSON.
- **Validação:** revisar dependências e testar regras sem depender de objetos HTTP.

#### F-09 — MEDIUM — Consultas N+1 nas listagens de pedidos

- **Catálogo:** AP-07.
- **Locais:** `models.py:171–201`, `203–233`.
- **Evidência:** após buscar pedidos, executa consulta por pedido e consulta adicional por item para obter o nome do produto.
- **Impacto e classificação:** o número de consultas cresce com a quantidade de pedidos e itens; não foi feita medição de latência.
- **Correção e compatibilidade:** JOIN ou consultas em lote, mantendo estrutura do JSON e tratamento de relações históricas ausentes.
- **Validação:** comparar respostas e contar consultas com diferentes volumes de pedidos.

#### F-10 — MEDIUM — Erros e logs tratados de forma dispersa

- **Catálogo:** AP-10.
- **Locais:** `controllers.py:8–12`, `57–62`, `95–96`, `106–109`, `161–165`, `179–186`, `218–220`, `291–292`; `app.py:77–78`.
- **Evidência:** capturas amplas devolvem `str(e)`; mensagens usam `print`, com formatos e contexto inconsistentes.
- **Impacto e classificação:** erros esperados tornam-se `500`, detalhes internos chegam ao cliente e o diagnóstico perde padronização.
- **Correção e compatibilidade:** fronteira central de erros, respostas sanitizadas e logging com nível/contexto, sem credenciais.
- **Validação:** JSON malformado, conversões inválidas e falha interna controlada; status correto, rollback e logs sem dados sensíveis.

#### F-11 — LOW — Política de desconto expressa em valores sem nomes

- **Catálogo:** AP-12.
- **Local:** `models.py:256–262`.
- **Evidência:** limiares e percentuais comerciais aparecem diretamente nas condições.
- **Impacto e classificação:** manutenção da regra exige interpretar literais; não há evidência de erro de cálculo atual.
- **Correção e compatibilidade:** nomear a política no serviço de relatório, preservando comparações estritas `>` e arredondamento.
- **Validação:** valores abaixo, iguais e acima de cada limiar.

### APIs deprecated

Nenhuma chamada foi confirmada como deprecated nesta aplicação. Não foram atribuídos findings por idade da biblioteca ou estilo do código. A versão da biblioteca SQLite em execução não foi verificada.

### Comparação com a análise manual do passo a passo

Os IDs abaixo pertencem à tabela manual do roteiro; os cenários da baseline usam numeração semelhante, mas representam outra coisa.

| Referência em `PLANO_EXECUCAO.md` | Finding | Resultado |
|---|---|---|
| P1-01 — SQL no login | F-01 | Confirmado |
| P1-02 — N+1 | F-09 | Confirmado |
| P1-03 — Tipos/conversões | F-07 | Confirmado; severidade maior pelo impacto adicional no estoque |
| P1-04 — Valores de desconto | F-11 | Confirmado |
| P1-05 — Logs com `print` | F-10 | Confirmado, consolidado com tratamento de erros |

Foram confirmados **cinco problemas documentados no roteiro**, além dos achados adicionais. Os mínimos de cinco findings e um CRITICAL/HIGH foram atingidos. O README ainda não contém uma seção formal de “Análise Manual”; essa é uma pendência documental, não evidência de execução independente.

### Refatoração MVC proposta

Estrutura prevista dentro da aplicação:

```text
app.py                       # entrada preservada
src/
  __init__.py                # factory e composição
  config.py
  database.py                # conexão e transações
  errors.py
  models/                    # persistência por domínio
  controllers/               # coordenação dos casos de uso
  services/                  # pedidos, relatórios e administração
  views/                     # rotas e serializers JSON
tests/                       # regressão e validação HTTP
```

Ordem de execução:

1. Salvar esta auditoria, preservando os locais e hashes anteriores à refatoração.
2. Extrair configuração, conexão e tratamento de erros: F-02, F-05 e F-10.
3. Separar responsabilidades e parametrizar SQL: F-01 e F-08.
4. Implementar migração de senhas e autenticação/autorização: F-03 e F-04.
5. Corrigir validação e integridade dos pedidos: F-06 e F-07.
6. Eliminar N+1 e explicitar descontos: F-09 e F-11.
7. Validar o código corrente e registrar resultados separados da auditoria.

**Autenticação proposta:** HTTP Basic nas operações protegidas, verificando o hash e carregando o papel do usuário do banco em cada requisição. Isso permite preservar o JSON de `/login` sem inventar tokens. O administrador será provisionado por comando local explícito; cadastro público cria apenas `cliente`.

| Contrato | Comportamento proposto |
|---|---|
| Raiz, health, leitura de produtos, cadastro e login | Públicos; respostas válidas preservadas, sem campos sensíveis. |
| Escrita de produtos, listagem de usuários, pedidos gerais, status e relatório | Administrador. |
| Detalhe de usuário e pedidos por usuário | Próprio usuário ou administrador. |
| Criação de pedido | Próprio usuário; administrador pode indicar outro usuário existente. |
| Credenciais ausentes/incorretas | `401`; identidade válida sem permissão: `403`. |
| `/admin/query` | Administrador; manter `sql`, aceitando apenas quatro consultas predefinidas de contagem das tabelas. SQL livre retorna `400`. A consulta de contagem da baseline continua disponível. |
| `/admin/reset-db` | Administrador, habilitação explícita em banco descartável e confirmação `{"confirmacao":"RESET"}`. Operação permitida apaga as quatro tabelas em transação; desabilitada retorna `403`. |
| Entradas inválidas | `400`, sem gravações. Recursos inexistentes: `404`. Produto referenciado: `409` na exclusão. |

As **19 operações continuarão implementadas**. Notificações permanecerão simuladas. A regra atual de relatório será preservada, incluindo tratamento dos status; restituição de estoque no cancelamento não está incluída neste plano.

**Preservação e migração dos dados:**

- Os testes usarão bancos descartáveis; não executarão reset, seed ou migração no `loja.db` local.
- A migração será explícita, transacional e idempotente, com versão registrada, preservando IDs e relações. Não distinguirá senha textual de hash apenas pelo prefixo.
- Credenciais fixas de demonstração deixarão de ser criadas no boot. O administrador de demonstração legado precisará de redefinição local para recuperar acesso administrativo.
- Órfãos existentes serão diagnosticados antes de impor novas restrições. Conflitos interromperão a migração sem excluir ou reparar dados silenciosamente.
- A localização padrão do banco será preservada; importação e boot não popularão dados automaticamente.

### Plano de validação

A [baseline histórica](baseline-project-1.md) será referência dos contratos. O executor atual usa `git archive` de um commit fixo e **não valida a futura refatoração**. Será criado um executor que carregue o código editado e use HTTP real em loopback.

Boot previsto, após preparar o banco descartável e as fixtures:

```bash
DATABASE_PATH=/tmp/<diretorio-de-teste>/loja.db .venv/bin/python app.py
```

A matriz resume os fluxos históricos válidos; os casos de autorização serão acrescentados conforme a política proposta.

| Método e rota | Entrada | Status histórico | Campos relevantes | Efeito no banco | Preservar ou corrigir |
|---|---|---:|---|---|---|
| `GET /` | — | 200 | mensagem, versão, endpoints | Nenhum | Preservar |
| `GET /health` | — | 200 | status, database, counts | Nenhum | Remover segredo/configuração interna |
| `GET /produtos` | — | 200 | dados, sucesso | Nenhum | Preservar |
| `GET /produtos/<id>` | ID | 200/404 | dados/erro | Nenhum | Preservar |
| `GET /produtos/busca` | termo, categoria, preços | 200; tipo inválido: 500 | dados, total | Nenhum | Inválido passa a 400 |
| `POST /produtos` | Produto válido | 201 | id, mensagem | Insere produto | Autorizar; aceitar apóstrofo |
| `PUT /produtos/<id>` | Produto válido | 200/404 | sucesso/erro | Atualiza campos | Autorizar e validar |
| `DELETE /produtos/<id>` | ID | 200/404 | mensagem/erro | Remove produto | Autorizar; referenciado: 409 |
| `GET /usuarios` | — | 200 | dados | Nenhum | Administrador; sem senha |
| `GET /usuarios/<id>` | ID | 200/404 | dados/erro | Nenhum | Proprietário/admin; sem senha |
| `POST /usuarios` | nome, email, senha | 201/400 | id/erro | Insere usuário | Armazenar hash |
| `POST /login` | email, senha | 200/401/400 | usuário público/erro | Nenhum | Preservar sem SQL concatenado |
| `POST /pedidos` | usuário, itens | 201/400 | pedido_id, total | Pedido, itens, estoque | Autorizar; rejeitar estado inválido |
| `GET /pedidos` | — | 200 | dados com itens | Nenhum | Administrador; eliminar N+1 |
| `GET /pedidos/usuario/<id>` | ID | 200 | dados com itens | Nenhum | Proprietário/admin; eliminar N+1 |
| `PUT /pedidos/<id>/status` | status | 200/400 | mensagem/erro | Atualiza status | Admin; inexistente passa a 404 |
| `GET /relatorios/vendas` | — | 200 | totais, descontos, status | Nenhum | Administrador; preservar cálculos |
| `POST /admin/query` | SQL de contagem | 200/400 | dados/erro | Nenhum no teste | Administrador; consultas limitadas |
| `POST /admin/reset-db` | Confirmação proposta | 200 anônimo | mensagem, sucesso | Apaga quatro tabelas | Negar anônimo; validar operação autorizada isolada |

Além dos 39 cenários históricos, serão verificados:

- JSON ausente, malformado ou com estrutura/tipos incorretos; números não finitos.
- Quantidade zero, negativa ou fracionária; produto repetido excedendo estoque agregado.
- Recusa sem alteração de campos, estoque ou registros; rollback em falha intermediária.
- Migração de senha, repetição idempotente e autenticação após migração.
- Permissões, propriedade, credenciais inválidas e ausência de dados sensíveis.
- Contagem de consultas, limiares de desconto e inventário real das 19 operações.

**Estado atual:** análise e auditoria concluídas; boot e validação do código refatorado ainda não executados. Nenhum arquivo foi alterado por esta execução.

**Posso salvar este relatório em `reports/audit-project-1.md` e iniciar a Fase 3 com a refatoração, as mudanças de contrato e o plano de validação apresentados?**

A pausa é exigida pela [SKILL.md](../code-smells-project/.agents/skills/refactor-arch/SKILL.md): “Then stop and wait for an explicit answer”, e pelo [passo a passo](../PLANO_EXECUCAO.md#9-execute-e-valide-o-projeto-1), que exige confirmação antes de modificar qualquer arquivo.
