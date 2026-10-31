**Auditoria — `ecommerce-api-legacy`**

**Estado auditado**

- **Repositório:** `/home/mateus/projetos/mateus/mba/mba-ia-refactor-projects-skill`.
- **Projeto:** `ecommerce-api-legacy/`.
- **Data da coleta:** 31/10/2026, UTC−03.
- **Ferramenta:** Codex; identificador exato do modelo indisponível.
- **HEAD:** `06c8b2b9e82f954910f6a7494dc10bbe2eeae568`.
- **Commit-base do roteiro:** `6d1ce6248c3e956801010a89d8bdaab48029bf30`.
- **Correspondência:** fontes, manifesto, lockfile e documentação do projeto coincidem com o commit-base.
- **Alterações preexistentes:** `SKILL.md` e suas cinco referências estão modificados localmente. Também existem alterações na skill do projeto vizinho. Serão preservadas.
- **Destino proposto:** `reports/audit-project-2.md`, na raiz do repositório.

Hashes SHA-256 dos fontes auditados:

```text
src/AppManager.js
fe40e39220536fe666a9af818c259ab5844ee77fac556211770f4997650b4104

src/app.js
d2096cb2ff25af262c63053fc861605979ae270c8949e9ebabf7de18e76ffc4c

src/utils.js
58eebf3e99911451cd54b3a6f42f1b3f123ef0d4e8f6dd60c55444ed2b45333d
```

**Análise do projeto**

| Campo | Resultado |
|---|---|
| Linguagem e runtime | JavaScript/CommonJS; Node.js `v24.19.0`, npm `11.17.0`. |
| Framework | Express: declarado `^4.18.2`; lockfile e instalação existentes: `4.22.1`. |
| Persistência | Pacote sqlite3: declarado `^5.1.6`; lockfile e instalação: `5.1.7`. Versão do motor SQLite não verificada. |
| Domínio | LMS: usuários, cursos, matrículas, pagamentos e relatório financeiro. |
| Banco | SQLite em memória, recriado a cada processo. Inicialização cria cinco tabelas e popula dados demonstrativos. |
| Entrada | `src/app.js`; comando `npm start`. |
| Arquitetura | `AppManager` concentra conexão, schema, seeds, rotas, regras, pagamentos simulados e respostas. |
| Inventário | 3 arquivos JavaScript, 180 linhas físicas, incluindo comentários e linhas vazias; 3 operações HTTP explícitas. |
| Exclusões | Dependências, `.agents`, arquivos gerados, documentação e evidências. Manifesto e lockfile examinados separadamente. |
| Integrações | Pagamento simulado pelo prefixo do cartão; nenhum gateway externo é chamado. |

A [baseline histórica](baseline-project-2.md) foi executada em **30/10/2026, às 02:09:49 UTC**, sobre cópia isolada do commit-base: **3/3 operações, 14 cenários e 6 desvios**.

Nesta execução houve somente inspeção estática e leitura de evidências. Boot, requisições, seeds e instalações não foram executados.

**Resumo dos achados**

| CRITICAL | HIGH | MEDIUM | LOW | Total |
|---:|---:|---:|---:|---:|
| 2 | 3 | 3 | 2 | **10** |

Os caminhos abaixo são relativos a `ecommerce-api-legacy/`.

**F-01 — CRITICAL — Dados de cartão e configuração registrados em log**

- **Catálogo e locais:** AP-02; `src/AppManager.js:43–46` e `src/utils.js:1–7`.
- **Evidência:** o checkout escreve no console o cartão recebido e o valor de `paymentGatewayKey`. A baseline também registrou esse comportamento, com valores mascarados.
- **Impacto e contexto:** dados sensíveis fornecidos pelo cliente chegam aos logs. Os literais de configuração aparentam ser demonstrativos; não há evidência de credenciais reais de produção.
- **Correção:** remover os valores sensíveis dos logs e retirar configurações sem uso. O simulador não precisa de chave real de pagamento.
- **Compatibilidade e verificação:** preservar aprovação/recusa simuladas; conferir respostas, erros e logs usando marcadores sintéticos para garantir que cartão, senha e segredo não apareçam.

**F-02 — CRITICAL — Operações sensíveis sem autenticação ou autorização**

- **Catálogo e locais:** AP-13; `src/app.js:5–10`; `src/AppManager.js:40–41`, `66–75`, `80–129` e `131–136`.
- **Evidência:** relatório e exclusão não verificam identidade. A baseline confirmou relatório anônimo e exclusão efetiva. No checkout, conhecer um email existente basta para reutilizar o usuário, sem conferir sua senha.
- **Impacto:** permite exclusão arbitrária de usuários e acesso administrativo, além de associação de compras a contas alheias.
- **Correção:** exigir credencial administrativa externa para relatório/exclusão e verificar a senha ao reutilizar uma conta no checkout.
- **Compatibilidade e verificação:** preservar os três endpoints. Acrescentar testes com credencial ausente, incorreta e válida; negativas devem preservar os dados.

**F-03 — HIGH — `AppManager` concentra responsabilidades de vários domínios**

- **Catálogo e locais:** AP-03, incorporando AP-04 sem contagem duplicada; `src/AppManager.js:4–137`.
- **Evidência:** a classe cria o banco e o schema (`5–22`), registra HTTP, conduz checkout (`28–78`), monta relatórios (`80–129`) e exclui usuários (`131–136`).
- **Impacto:** regras e persistência dependem diretamente de HTTP, dificultando testes isolados e ampliando o risco de regressão.
- **Correção:** separar composição, models, controllers, apresentação e serviço de checkout, com dependências injetadas.
- **Compatibilidade e verificação:** manter métodos, caminhos e formatos válidos; revisar a direção das dependências e exercitar todas as operações.

**F-04 — HIGH — Armazenamento inadequado de senhas**

- **Catálogo e locais:** AP-05; `src/utils.js:17–22`; `src/AppManager.js:18` e `66–70`.
- **Evidência:** `badCrypto` repete fragmentos de Base64 e trunca o resultado. Cadastro sem senha recebe um valor padrão; o seed armazena senha textual.
- **Impacto:** a transformação não oferece proteção adequada de senha e produz colisões facilmente. A ausência de verificação no checkout integra F-02.
- **Correção:** usar hash de senha com salt aleatório, por meio de `crypto.scrypt`, e comparação apropriada. Exigir senha no cadastro.
- **Dados e verificação:** não há banco persistente configurado a migrar. Seeds de teste usarão senha sintética fornecida explicitamente; testar hashes diferentes para senhas iguais e aceitação/rejeição das credenciais.

**F-05 — HIGH — Escritas sem atomicidade e relações órfãs**

- **Catálogo e locais:** AP-14; `src/AppManager.js:12–21`, `43–75` e `131–135`.
- **Evidência:** usuário, matrícula, pagamento e auditoria são gravados sem transação explícita. A recusa ocorre depois da criação do usuário. Exclusão não possui política para dependências; o schema não declara chaves estrangeiras.
- **Confirmação histórica:** pagamento recusado criou usuário; exclusão deixou duas matrículas órfãs.
- **Impacto:** falhas podem deixar estado parcial e comprometer a coerência de usuários, matrículas e valores financeiros.
- **Correção:** checkout transacional, rollback e coordenação das operações sobre a conexão. Rejeitar exclusão de usuário com dependências com `409`.
- **Verificação:** recusa e falha intermediária não devem deixar registros parciais. Exclusão impedida deve preservar dados e receita; usuário sem dependências deve poder ser removido.

**F-06 — MEDIUM — Consultas N+1 no relatório**

- **Catálogo e local:** AP-07; `src/AppManager.js:83–106`.
- **Evidência:** após consultar cursos, executa consulta por curso e novas consultas de usuário/pagamento por matrícula.
- **Impacto:** trabalho no banco cresce com o volume do relatório. Não houve medição nova de latência ou quantidade de consultas.
- **Correção:** JOINs ou consultas em lote, mantendo cursos sem matrícula e receita apenas de pagamentos `PAID`.
- **Compatibilidade e verificação:** preservar `course`, `revenue` e `students`; comparar valores e medir consultas com diferentes volumes de fixtures.

**F-07 — MEDIUM — Validação insuficiente de entradas**

- **Catálogo e locais:** AP-08; `src/AppManager.js:29–38`, `45–46` e `131–135`.
- **Evidência:** checagens de presença não validam tipos, formato de email ou identificadores. `startsWith` é aplicado diretamente ao cartão recebido.
- **Confirmação histórica:** email inválido foi persistido; cartão numérico provocou `TypeError` e encerrou o processo.
- **Correção:** validar estrutura JSON, tipos, limites, email e IDs antes das operações. A exigência de senha será tratada em conjunto com F-04.
- **Verificação:** entradas inválidas retornam `400`, sem gravações; o processo permanece disponível para a próxima requisição.

**F-08 — MEDIUM — Erros assíncronos ignorados e respostas inconsistentes**

- **Catálogo e locais:** AP-10; `src/AppManager.js:37–38`, `57–60`, `92–106` e `133–135`.
- **Evidência:** erro de banco pode virar “curso não encontrado”; callbacks ignoram erros antes de acessar resultados; auditoria e exclusão podem responder sucesso apesar de falha.
- **Impacto:** respostas enganosas, exceções fora da fronteira HTTP e diagnósticos incompletos.
- **Correção:** propagar falhas assíncronas explicitamente no Express 4 e centralizar a tradução de erros, com respostas sanitizadas.
- **Verificação:** falhas controladas de consulta/gravação devem retornar `500` genérico, preservar atomicidade e permitir requisições seguintes. Recursos inexistentes continuam distinguíveis por `404`.

**F-09 — LOW — Nomes internos ambíguos**

- **Catálogo e local:** AP-11; `src/AppManager.js:29–33`, com usos no checkout.
- **Evidência:** `u`, `e`, `p`, `cid` e `cc` representam conceitos distintos do domínio.
- **Impacto:** dificultam leitura e manutenção do fluxo.
- **Correção:** adotar nomes internos como `userName`, `email`, `password`, `courseId` e `card`.
- **Compatibilidade e verificação:** preservar os campos públicos `usr`, `eml`, `pwd`, `c_id` e `card`; conferir o mapeamento nos testes HTTP.

**F-10 — LOW — Código morto e cache sem consumidor**

- **Catálogo e locais:** AP-12; `src/utils.js:9–14`, `25`; `src/AppManager.js:2`, `59`.
- **Evidência:** `totalRevenue` é declarado, exportado e importado sem uso. O cache recebe escritas, mas nenhum fluxo lê seus dados. `logAndCache` é chamado; não foi classificado como função nunca executada.
- **Impacto:** estado e dependências sem benefício funcional demonstrado.
- **Correção:** remover `totalRevenue` e o cache sem consumidor.
- **Compatibilidade e verificação:** relatório continuará derivado do banco; comparar seus valores antes/depois e revisar referências remanescentes.

**APIs deprecated**

Nenhuma chamada foi confirmada como deprecated nos fontes examinados. `Buffer.from()` não foi classificado como obsoleto. Não foram criados findings com base apenas na idade das bibliotecas ou no estilo de callbacks.

**Comparação com a análise manual**

| Achado em `PLANO_EXECUCAO.md:202–206` | Auditoria | Resultado |
|---|---|---|
| P2-01 — Cartão/chave no log | F-01 | Confirmado |
| P2-02 — N+1 | F-06 | Confirmado |
| P2-03 — Validação de tipos | F-07 | Confirmado |
| P2-04 — Abreviações | F-09 | Confirmado |
| P2-05 — `totalRevenue` sem uso | F-10 | Confirmado |

Foram confirmados os **cinco problemas manuais do roteiro**. Os mínimos de cinco findings e um CRITICAL/HIGH foram atendidos. O README ainda contém requisitos para a análise manual, sem uma tabela P2 concluída; isso permanece uma pendência documental.

**Refatoração MVC proposta**

Estrutura prevista, ajustável durante a implementação:

```text
src/
  app.js                 # composição e entrada preservada
  config.js
  database.js            # conexão, schema e transações
  errors.js
  models/                # persistência por domínio
  controllers/           # coordenação dos casos de uso
  services/              # checkout e pagamento simulado
  views/                 # rotas e apresentação JSON
tests/
  run-validation.js
```

Ordem de execução:

1. Salvar esta auditoria antes de editar os fontes.
2. Separar configuração, banco, erros e composição: F-01, F-03 e F-08.
3. Implementar senhas e autorização: F-02 e F-04.
4. Corrigir validação, transações e integridade: F-05 e F-07.
5. Otimizar relatório e limpar nomes/código: F-06, F-09 e F-10.
6. Validar o código corrente e salvar resultados separados em `reports/validation-project-2.md` e `reports/evidence/validation-project-2.*`.

**Contratos propostos para aprovação**

| Operação | Comportamento proposto |
|---|---|
| `POST /api/checkout` | Preservar campos públicos e sucesso `200 {msg:"Sucesso", enrollment_id}`. Conta nova exige senha; conta existente exige senha correta, com `401` se incorreta. |
| Pagamento simulado | Preservar aprovação pelo prefixo textual `4` e recusa `400`; não registrar nem armazenar cartão. Recusa não deixará usuário ou outras gravações. |
| Curso inexistente | Preservar `404`, sem gravações. |
| JSON, tipos, email ou IDs inválidos | `400`, sem gravações e sem encerrar o processo. |
| `GET /api/admin/financial-report` | Preservar array e campos existentes; exigir Bearer administrativo configurado por `ADMIN_API_TOKEN`. |
| `DELETE /api/users/:id` | Exigir a mesma autorização. Usuário sem dependências: `200`; com matrículas/pagamentos: `409`; inexistente: `404`; ID inválido: `400`. A mensagem de sucesso deixará de afirmar que ficaram dados órfãos. |
| Autorização administrativa | Token gerado externamente, sem fallback no código; ausência ou valor incorreto retorna `401`. Sem configuração, o acesso permanece bloqueado. Provisionamento e teste serão documentados. |
| Inicialização | Manter banco em memória. Preparar schema antes de aceitar requisições; seed demonstrativo será explícito, com senha fornecida por ambiente, preservando as fixtures históricas para comparação. |

Todas as três operações continuarão implementadas. O pagamento permanecerá simulado.

A conexão terá ciclo de vida definido e encerramento controlado. A coordenação transacional abrangerá operações completas; apenas chamar `db.serialize()` não será tratado como garantia suficiente de isolamento.

**Preservação de dados**

O legado usa exclusivamente banco em memória; não há migração de arquivo persistente prevista. Os testes utilizarão instâncias descartáveis. Nenhum banco de outro projeto será alterado. Eventual necessidade de suportar um banco persistente existente exigirá revisar esse plano.

**Plano de validação**

A baseline histórica será referência, com estas diferenças intencionais: autorização, verificação de senha, rejeição de entradas inválidas, atomicidade e política de exclusão.

| Método e rota | Entrada/cenário | Baseline observada | Resposta relevante | Efeito no banco | Validação proposta |
|---|---|---|---|---|---|
| `POST /api/checkout` | Conta nova e existente, pagamento aprovado | `200` | `msg`, `enrollment_id` | Usuário quando novo, matrícula, pagamento e auditoria | Preservar valores; verificar senha e persistência |
| `POST /api/checkout` | Pagamento recusado | `400` | Texto de recusa | Legado criou usuário | Corrigir para nenhuma gravação |
| `POST /api/checkout` | Curso inexistente/campos ausentes | `404`/`400` | Erro | Sem gravações | Preservar |
| `POST /api/checkout` | Email inválido, senha ausente, cartão numérico | Aceitação indevida ou queda do processo | Inconsistente | Gravações indevidas ou estado não confirmado | `400`, nenhuma gravação, processo disponível |
| `GET /api/admin/financial-report` | Antes/depois de compras | `200` | `course`, `revenue`, `students` | Nenhum | Autorizar e preservar cálculos; medir consultas |
| `DELETE /api/users/:id` | Usuário matriculado | `200` | Sucesso com aviso | Usuário removido e relações órfãs | `409`, estado e receita preservados |
| `DELETE /api/users/:id` | Inexistente/sem dependências | Inexistente retornava `200`; sem dependências não coberto | Texto | Nenhuma remoção/remoção autorizada | `404`/`200`, com fixture específica |
| Relatório e exclusão | Credencial ausente, incorreta e válida | Acesso anônimo permitido | Dados/sucesso | Exclusão possível | Negar indevidos e comprovar operação autorizada |

Após aprovação:

- Iniciar o código editado por `npm start`, em loopback, com configuração e fixtures sintéticas.
- Executar testes HTTP reais das **3/3 operações**, incluindo os 14 cenários históricos adaptados.
- Conferir registros, valores financeiros, vínculos e ausência de alterações nas negativas.
- Injetar falha intermediária para comprovar rollback e recuperação.
- Verificar senhas, ausência de dados sensíveis nos logs e consultas do relatório.
- Registrar comandos, versões, resultados e limitações.

O executor `scripts/baseline/run.py` usa `git archive` de um commit fixo; será criado um executor para os fontes correntes. Executar novamente a baseline antiga não comprovaria a refatoração.

**Estado:** análise e auditoria concluídas; refatoração, boot e validação ainda pendentes.

**Posso salvar este relatório em `reports/audit-project-2.md` e iniciar a Fase 3 com a refatoração, as mudanças de contrato e o plano de validação apresentados?**

Essa confirmação é exigida pela [SKILL.md](../ecommerce-api-legacy/.agents/skills/refactor-arch/SKILL.md), que determina “Then stop and wait for an explicit answer”, e pelo [passo a passo](../PLANO_EXECUCAO.md), que exige revisão humana antes de modificar qualquer arquivo.
