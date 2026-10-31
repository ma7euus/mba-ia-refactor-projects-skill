# Validação — ecommerce-api-legacy

Fase 3 da skill `refactor-arch` concluída após a resposta humana **“sim”** ao
relatório e plano apresentados. A [auditoria original](audit-project-2.md) foi
salva antes das alterações e mantém os caminhos, linhas e hashes do legado.
O status pendente no texto original representa aquele momento da revisão.

## Estado e comandos executados

- Alvo exclusivo: `ecommerce-api-legacy/`, com evidências em `reports/`.
- Commit-base legado: `6d1ce6248c3e956801010a89d8bdaab48029bf30`.
- HEAD na auditoria: `06c8b2b9e82f954910f6a7494dc10bbe2eeae568`.
- HEAD na validação: `a32e2c499493ba0cabcb66b9707de104161393f4`. Um commit externo
  de criação da skill ocorreu durante a execução, apenas nos 12 arquivos da
  skill de P2/P3. Não houve commit realizado por esta execução, nem alteração
  dos fontes auditados por esse commit. As alterações preexistentes foram
  preservadas. Código refatorado e evidências estão no worktree.
- Testes: **2026-10-31T03:29:59.944Z**; smoke de startup:
  **2026-10-31T03:31:44.166Z**.
- Ambiente real: Node `v24.19.0`, npm `11.17.0`, Express `4.22.1`, sqlite3
  `5.1.7`, motor SQLite `3.44.2`. Manifesto e dependências foram preservados;
  apenas o script `npm test` foi adicionado.

Na raiz do projeto:

```bash
npm test -- --json ../reports/evidence/validation-project-2.json \
  > ../reports/evidence/validation-project-2.log 2>&1
```

**Exit code 0; 34/34 cenários passaram; 3/3 operações exercitadas.**

O teste importa os fontes correntes, sem checkout/archive do legado, inicia
Express com HTTP real em loopback e porta efêmera, e cria um SQLite em memória
por instância. Credenciais sintéticas são aleatórias e ficam apenas em memória.
O JSON registra SHA-256 dos 16 arquivos JavaScript atuais de `src/`.

O sandbox recusou `listen` com `EPERM` na primeira tentativa de boot. Após
identificar o bloqueio, os testes HTTP foram executados com escalonamento
aprovado para loopback; não foram feitas mudanças de código para contornar a
restrição. Não houve instalação de dependências nem acesso a serviços externos.

Também foi executado **`npm start` real**, por subprocesso, com `HOST=127.0.0.1`,
`PORT=0`, `SEED_DEMO_DATA=1` e senha/token aleatórios fornecidos via ambiente.
O smoke verificou relatório autorizado `200`, relatório anônimo `401`, receita
inicial `997`, checkout `200` e exclusão de usuário matriculado `409`. O grupo
de processos criado pelo smoke foi encerrado com SIGTERM. Não ficaram servidores
de teste intencionalmente ativos.

O [README do projeto](../ecommerce-api-legacy/README.md) fornece os comandos
reproduzíveis de provisionamento e startup. O teste principal também verifica
boot sem seed e bloqueio administrativo quando não há token configurado.

## Estrutura antes/depois

Antes: três arquivos de aplicação, **180 linhas físicas**, com `AppManager`
concentrando HTTP, schema, seeds, consultas, regras e pagamento simulado.

Depois: **16 arquivos de aplicação, 547 linhas físicas**, mais um executor de
validação com 595 linhas. Contagem inclui comentários e linhas vazias; exclui
dependências, skill, documentação e evidências. Crescimento inclui controles de
segurança, atomicidade, configuração e tratamento de erros antes inexistentes.

```text
src/
  app.js                    # composição, factory e startup
  config.js                 # configuração externa validada
  database.js               # schema, conexão, fila, transações e fechamento
  seed.js                   # demonstração explicitamente habilitada
  errors.js                 # tradução central de erros
  models/
    users.js, courses.js, enrollments.js, payments.js, audit.js, reports.js
  controllers/index.js      # fluxo dos casos de uso
  services/
    checkout.js, passwords.js, payment.js
  views/routes.js           # HTTP, autenticação e serializers
tests/run-validation.js     # HTTP real dos fontes correntes
```

`AppManager.js` e `utils.js` foram removidos após conferir que não havia
consumidores fora da implementação substituída. Os fontes originais permanecem
recuperáveis pelo commit-base e pelos hashes da auditoria.

## Disposição dos findings

Os caminhos de correção abaixo são relativos ao projeto. Todos os achados da
auditoria aprovada receberam correção e verificação; isso não é uma declaração
de ausência universal de anti-patterns.

| Finding | Correção implementada | Verificação real | Estado |
|---|---|---|---|
| F-01 / AP-02 | Remoção do log de cartão/chave e da configuração sem consumidor; `services/payment.js`, `errors.js:30–34`. | OUTPUT-01 e smoke: zero marcadores sensíveis em respostas/logs; cartão não é persistido. | Corrigido |
| F-02 / AP-13 | Bearer administrativo externo em `views/routes.js:8–20`; senha de conta existente em `services/checkout.js:40–43`; sem fallback. | P2-10, AUTH-01/02/03/04; acessos negados sem mutação; relatório e exclusão autorizados realmente exercitados. | Corrigido |
| F-03 / AP-03, AP-04 | Composição em `app.js:10–25`; models sem HTTP; controllers de coordenação; serviço transacional e views explícitas. | Revisão de dependências e HTTP das 3 operações; startup pela factory e por `npm start`. | Corrigido |
| F-04 / AP-05 | `services/passwords.js`: scrypt versionado com salt aleatório, parâmetros fixos e comparação segura; seed com senha explícita. | PASSWORD-01, CONFIG-01 e AUTH-03: salts independentes, senha correta/incorreta e seed sem texto puro. | Corrigido |
| F-05 / AP-14 | `database.js:16–25,49–107`: FKs RESTRICT e fila para casos completos; checkout transacional; `controllers/index.js:26–38` impede exclusão com dependências. | P2-05/11, ROLLBACK-01/02, CONCURRENCY-01/02 e INTEGRITY-01; falhas não deixam gravações parciais nem relações órfãs. | Corrigido |
| F-06 / AP-07 | `models/reports.js:1–25`: uma consulta LEFT JOIN, com agrupamento em memória e ordenação estável. | REPORT-01: uma consulta no volume pequeno e após adicionar 25 cursos; resultado do model comparado ao HTTP; receita apenas PAID. | Corrigido |
| F-07 / AP-08 | `services/checkout.js:10–28`; IDs em `controllers/index.js:5–14`; limites do parser. | P2-06/07/08/09/14 e INPUT-01–05; JSON, tipos, limites, curso inativo e identificadores inválidos; processo permanece disponível. | Corrigido |
| F-08 / AP-10 | Promessas dos callbacks SQL, wrapper async no Express 4 e `errors.js` central; startup encerra recursos em falha. | ROLLBACK-01/02 e ERROR-01: erro SQL controlado vira 500 sanitizado, rollback e recuperação. Parser/URI/charset com 4xx. | Corrigido |
| F-09 / AP-11 | `userName`, `email`, `password`, `courseId`, `enrollmentId` nos fluxos novos; chaves públicas preservadas. | P2-02/03/04 verificam payload e formato; revisão estática das referências. | Corrigido |
| F-10 / AP-12 | Removidos `totalRevenue`, cache sem leitor e dependências antigas de `utils`. | Busca de referências nos fontes; receita derivada do banco, comprovada em P2-01/03/04/12 e REPORT-01. | Corrigido |

Não foi confirmada API deprecated aplicável aos fontes desta aplicação. Nenhum
finding foi criado apenas pela idade da biblioteca ou por usar callbacks.

## Comparação de comportamento

Os IDs abaixo retomam os cenários da baseline, e não os IDs da tabela manual.
Como entradas antes aceitas passam a ser rejeitadas, o estado acumulado muda:
receita `2491` no P2-12 refatorado é coerente com os três pagamentos válidos,
enquanto o legado chegava a `3485` após aceitar cadastros inválidos.

| Cenário | Legado observado | Refatorado observado |
|---|---|---|
| P2-01: relatório inicial | 200 anônimo; 2 cursos e receita997 | 200 autorizado, mesmo formato/receita; anônimo401 |
| P2-02: conta nova/checkout | 200, usuário/matrícula/pagamento/auditoria | 200, mesmos efeitos válidos, senha com hash |
| P2-03: relatório pós-compra | Receita1994 | Receita1994 e aluno incluído |
| P2-04: conta existente/outro curso | Reutiliza email sem verificar senha | Senha válida reutiliza usuário; pagamento497 e receita2491 |
| P2-05: pagamento recusado | 400, mas cria usuário | 400, todos os registros/campos inalterados |
| P2-06: campos ausentes | 400 | 400 sem mutação |
| P2-07: curso inexistente | 404 | 404 sem mutação |
| P2-08: conta nova sem senha | 200 com senha padrão | 400 sem mutação |
| P2-09: email inválido | 200 e cadastro persistido | 400 sem mutação |
| P2-10: relatório anônimo | 200 | 401 |
| P2-11: exclusão de matriculado | 200 com duas matrículas órfãs | 409, usuário/relações/valores preservados |
| P2-12: relatório após exclusão | Receita preservada com alunos Unknown | Receita válida preservada; nenhum Unknown |
| P2-13: exclusão inexistente | 200 enganoso | 404 sem mutação |
| P2-14: cartão numérico | Processo encerrou sem resposta | 400; próxima requisição200 |

Além desses 14 cenários, 20 cenários adicionais passaram. Eles incluem exclusão
autorizada de usuário **sem dependências** (`200`), duas falhas de gravação
injetadas via triggers temporários, consulta financeira com falha, concorrência,
FKs, limites e transporte, hashes e proteção das saídas.

Rejeições e rollback comparam os registros e campos completos das cinco tabelas
antes/depois, apenas em memória. Evidências exportam resultados e contagens
sanitizados, sem snapshots brutos, senhas, hashes de senha, cartões ou tokens.

## Checklist de validação

### Fase 1 — Análise

- [x] Linguagem, framework e domínio detectados corretamente.
- [x] Versões declaradas, resolvidas e instaladas distinguidas.
- [x] Inventário e exclusões explícitos; todas as três operações identificadas.
- [x] Estado auditado relacionado ao commit-base e às alterações preexistentes.

### Fase 2 — Auditoria

- [x] Relatório apresentado antes de qualquer escrita e salvo após aprovação.
- [x] Dez findings ordenados por severidade, com locais originais e evidência.
- [x] Cinco correspondências com a análise manual do passo a passo.
- [x] Depreciações avaliadas sem inventar ocorrência.
- [x] Pausa humana observada; aprovação expressa posterior ao relatório.

### Fase 3 — Refatoração

- [x] MVC com models, controllers, routes/serializers e entry point claro.
- [x] Configuração externa; sem senha/token administrativo padrão.
- [x] Senhas com hash e verificação; autorização administrativa efetiva.
- [x] Erros centralizados e encaminhamento async adequado ao Express4.
- [x] Transações, rollback, fila e integridade referencial verificados.
- [x] Boot da aplicação editada e comando `npm start` verificados.
- [x] Três operações preservadas, incluindo exclusão permitida e negada.
- [x] Matriz funcional com persistência e correções intencionais verificada.
- [x] Relatório financeiro com consulta constante e valores coerentes.
- [x] Cada finding relacionado à correção e à sua evidência.
- [x] Documentação e exemplos atualizados dentro do projeto-alvo.
- [x] `git diff --check` sem erros.

## Evidências e limites

- [JSON dos 34 cenários e hashes dos fontes](evidence/validation-project-2.json).
- [Log da execução com exit code0](evidence/validation-project-2.log).
- [Smoke do npm start e HTTP](evidence/validation-project-2-boot.log).
- [Executor dos fontes correntes](../ecommerce-api-legacy/tests/run-validation.js).
- [Baseline histórica](baseline-project-2.md), mantida sem alterações.

Revisão final das responsabilidades: SQL fica em models/schema/seed; rotas não
calculam receita nem executam SQL; controllers coordenam; serviço de checkout
aplica regras dentro da transação. Não foram encontrados consumidores restantes
de `badCrypto`, `globalCache`, `totalRevenue` ou `AppManager` em `src/`.

As verificações cobrem operações e cenários, sem medir cobertura de linhas ou
carga. Pagamentos continuam simulados; banco continua efêmero. A credencial
administrativa representa uma capacidade administrativa única, sem sistema de
papéis, expiração ou protocolo de login novo. Nenhuma integração externa ou
migração persistente foi alegada como validada.

Esta entrega se restringe ao projeto2 e aos relatórios aprovados. README global,
projeto3, publicação, avaliação de acionamento automático e commits da entrega
completa permanecem fora desta execução. Não foi feito commit, push ou publicação.
