# Validação — task-manager-api

A Fase 3 da skill `refactor-arch` foi concluída após a aprovação explícita
(`sim`) nesta conversa. A aplicação corrente iniciou em loopback e as **22
operações HTTP tiveram fluxos de sucesso verificados**. A correção C-01 rejeita
Unicode inválido com `400` sem gravações, preservando Unicode válido.

Esta execução aproveitou a refatoração MVC que já estava no worktree. Não
recriou as camadas existentes nem atribui à execução atual a autoria de todas
as correções anteriores. As auditorias permanecem separadas dos resultados:

- [Auditoria do legado, F-01–F-11](audit-project-3.md), preservada sem alterações.
- [Auditoria atual aprovada, C-01](audit-project-3-current.md), salva antes de editar a aplicação.
- [Manifesto anterior à correção](evidence/audit-project-3-current-snapshot.json), com os hashes individuais do snapshot revisado.
- [Baseline histórica](baseline-project-3.md), referente ao commit legado `6d1ce6248c3e956801010a89d8bdaab48029bf30`.

## Snapshot e ambiente

O commit-base do worktree continua sendo
`4245cdd94eff763f412e58a5cdbd0bb34eb2bd87`. Os fontes incluem alterações
preexistentes e não commitadas; o commit sozinho não identifica o código
validado. Os 37 arquivos Python correntes, incluindo testes, coincidem com os
hashes registrados **nas duas evidências**. Nenhum fonte mudou durante os testes.

Há 35 arquivos Python da aplicação, com 1.322 linhas físicas, e dois arquivos
de testes, com 950 linhas. A contagem inclui módulos vazios, comentários e linhas
em branco; exclui dependências, caches, bancos, skill e relatórios.

SHA-256 do manifesto ordenado dos 35 fontes da aplicação, no formato
`hash  caminho\n` relativo ao projeto:

```text
098193695dc438f5f022ccc8ca6e4dad005ab53e9897d4ecc1f821ca5432ff0a
```

| Componente | Versão observada |
|---|---|
| Python | 3.14.4 |
| Flask | 3.0.0 |
| Flask-SQLAlchemy | 3.1.1 |
| Flask-Cors | 4.0.0 |
| SQLAlchemy | 2.1.6 |
| Werkzeug | 3.1.9 |
| SQLite | 3.46.1 |

Execução HTTP: **31/10/2026, 14:55:42–14:55:45 UTC**
(11:55:42–11:55:45 UTC−03). Lifecycle: **14:55:23–14:55:27 UTC**.

## Alterações desta execução

| Arquivo relativo a `task-manager-api/` | Mudança |
|---|---|
| `services/text_validation.py` | Helper compartilhado `utf8_text`, que rejeita surrogates isolados com `AppError(400)` |
| `services/user_validation.py` | Validação UTF-8 de nome, email, senha e credenciais de login, preservando os limites distintos de cadastro e contas legadas |
| `services/task_rules.py` | Validação de título, descrição, tags, busca e campos textuais de categoria antes de consultas/gravações |
| `tests/run_validation.py` | 56 casos HTTP de Unicode; evidência JSON escapa caracteres inválidos sem perder o mascaramento de credenciais |
| `tests/check_lifecycle.py` | Versões, hashes antes/depois e check de fontes estáveis |
| `README.md` | Contrato de Unicode, comando lifecycle e links para os relatórios |

Os campos são verificados após seus guards de tipo. Campos opcionais nulos
continuam aceitos. Enums, cor e email de cadastro têm allowlists/regex que já
rejeitam caracteres fora do contrato. Não houve normalização ou truncamento de
senhas, alteração de banco padrão ou nova migração de schema nesta execução.

## Estrutura MVC verificada

```text
task-manager-api/
  app.py                     factory, composição, CLI e launcher
  config.py                  configuração por ambiente
  database.py                integração SQLAlchemy e foreign keys
  errors.py                  tradução central de erros e rollback
  routes/                    adaptação HTTP e registro das operações
  controllers/               coordenação de usuários, tarefas, categorias e relatórios
  models/                    entidades, sessões e repositories
  services/                  autenticação, validação, regras e cálculos
  views/                     autorização HTTP e campos públicos
  utils/                     relógio UTC e cálculo compartilhado
  seed.py                    população/reset explícitos
  tests/                     HTTP corrente, invariantes e lifecycle
```

Rotas delegam aos controllers; controllers usam serviços/repositories com sessão
injetada; consultas ficam nos repositories e representações públicas nas views.
Os serviços de regras não leem `request` nem importam rotas. O SMTP sem
consumidores permanece removido, sem introdução de envio de emails.

## Comandos e isolamento

Executados a partir de `task-manager-api/`:

```bash
.venv/bin/python -B tests/run_validation.py --output ../reports/evidence/validation-project-3.json > ../reports/evidence/validation-project-3.log 2>&1
.venv/bin/python -B tests/check_lifecycle.py --output ../reports/evidence/validation-project-3-lifecycle.json > ../reports/evidence/validation-project-3-lifecycle.log 2>&1
```

Ambos terminaram com código **0**. A primeira tentativa HTTP falhou por
`PermissionError` ao criar o socket no sandbox; o mesmo comando foi executado
com a permissão necessária para loopback e passou. Essa tentativa bloqueada não
foi contada como validação funcional bem-sucedida.

O runner HTTP iniciou o **`app.py` corrente**, pelo interpretador `.venv/bin/python
-B app.py`, com `HOST=127.0.0.1`, porta efêmera, debug desabilitado e
`DATABASE_URL` apontando para um SQLite temporário. O teste verificou readiness,
login administrativo e requisições HTTP reais. Somente as definições dos 57
cenários históricos foram reutilizadas; não houve execução por `git archive`.

Fixtures, alterações diretas, triggers de falha, seeds e exclusões usaram bancos
descartáveis. O check `V3-311` confirmou que o estado do banco local
`instance/tasks.db` permaneceu byte a byte preservado. Não houve instalação de
dependências, reset do banco local ou envio de mensagens externas.

## Resultados observados

| Medida | Resultado |
|---|---:|
| Operações HTTP inventariadas/exercitadas com sucesso | **22/22** |
| Requisições HTTP | **291** |
| Invariantes adicionais | **22** |
| Resultados totais do executor principal | **313** |
| Verificações do executor principal | **1.136** |
| Desvios / rotas não exercitadas / erro do runner | **0 / 0 / nenhum** |
| Casos HTTP de C-01 | **56**, com **226** verificações |
| Lifecycle/CLI | **21/21** |

Os `500` esperados nos cenários de falha injetada de banco são deliberados:
comprovam resposta sanitizada e rollback. Não representam falhas inesperadas
da suíte nem contratos a manter para entradas inválidas.

Cada operação abaixo teve ao menos uma resposta de sucesso, além dos status
negativos relacionados. IDs remetem ao JSON principal. `ID` nas rotas corresponde
ao conversor inteiro registrado no Flask.

| Método e rota | Exemplo de sucesso | Status observados na operação |
|---|---|---|
| `GET /` | V3-002 | 200 |
| `GET /health` | V3-003 | 200 |
| `GET /tasks` | V3-004 | 200, 401, 403 |
| `POST /tasks` | V3-029 | 201, 400, 403, 404 |
| `GET /tasks/ID` | V3-031 | 200, 400, 403, 404 |
| `PUT /tasks/ID` | V3-032 | 200, 400, 403, 404, 500 injetado |
| `DELETE /tasks/ID` | V3-053 | 200, 403, 404 |
| `GET /tasks/search` | V3-030 | 200, 400, 403 |
| `GET /tasks/stats` | V3-005 | 200 |
| `GET /users` | V3-006 | 200, 401, 403 |
| `POST /users` | V3-016 | 201, 400, 403, 409 |
| `GET /users/ID` | V3-098 | 200, 400, 401, 403, 404 |
| `PUT /users/ID` | V3-028 | 200, 400, 401, 403, 404 |
| `DELETE /users/ID` | V3-055 | 200, 401, 403, 404, 500 injetado |
| `GET /users/ID/tasks` | V3-010 | 200, 400, 403, 404 |
| `POST /login` | V3-020 | 200, 400, 401, 403 |
| `GET /reports/summary` | V3-008 | 200, 401, 403 |
| `GET /reports/user/ID` | V3-011 | 200, 400, 403, 404 |
| `GET /categories` | V3-007 | 200, 401 |
| `POST /categories` | V3-023 | 201, 400, 401, 403 |
| `PUT /categories/ID` | V3-027 | 200, 400, 403, 404 |
| `DELETE /categories/ID` | V3-056 | 200, 400, 403, 404 |

Essa tabela descreve os casos executados, não afirma testar todas as combinações
de erros em cada rota. Um `404` de registro inexistente foi acompanhado de fluxos
de sucesso da mesma operação; nenhuma rota foi considerada preservada apenas
por retornar `404`.

## Antes/depois e disposição dos achados

Antes da correção atual, três reproduções isoladas confirmaram `500`: cadastro
com senha surrogate, cadastro com nome surrogate e login com senha surrogate.
O registro sanitizado está em
[unicode-project-3-before.json](evidence/unicode-project-3-before.json).

Após a correção, `V3-225–V3-266` exercitaram **42 negativas**, combinando
surrogates high/low com cadastro, edição, login em contas com hash atual/MD5,
tarefas e categorias. Todas retornaram `400`, com fingerprint de todas as linhas
inalterado. Updates combinaram campos válidos e inválidos para detectar gravação
parcial. `V3-267–V3-280` cobriram sucessos e limpeza: acentos, emojis, par surrogate
JSON válido, combining mark sem normalização, persistência, busca, senha
verificável, login e revogação de sessão após troca de senha.

| Achado | Disposição e implementação | Evidência atual |
|---|---|---|
| **C-01 — Unicode inválido** | **Corrigido nesta execução** por `services/text_validation.py`, consumido por `user_validation.py` e `task_rules.py` | 56 casos/226 verificações aprovados; 42 negativas sem escrita |
| F-01 — Hash exposto | Correção preexistente verificada: `views/users.py` seleciona campos públicos | Toda resposta HTTP é verificada contra campos de senha/hash; evidências mascaram tokens |
| F-02 — Falta de autorização | Correção preexistente verificada: bearer persistido por digest, expiração e checks de papel/propriedade | Token ausente/inválido/expirado, inatividade, recurso alheio, promoção e ações administrativas negadas sem escrita; sucessos autorizados |
| F-03 — MD5 | Correção preexistente verificada: hashes Werkzeug com salt e migração no login correto | V3-210–V3-219: senha errada/inatividade não migram; login correto migra; salts distintos; credenciais legadas longas continuam válidas |
| F-04 — Regras/persistência nas rotas | Separação MVC preexistente revisada estaticamente | Rotas finas e dependências por camada; 22 operações com fluxos de sucesso |
| F-05 — Configuração e efeitos implícitos | Configuração externa, comandos e seed explícitos preexistentes verificados | Lifecycle: import não cria SQLite; schema aditivo/idempotente; contas/IDs/valores legados preservados; admin sem sobrescrita; seed exige URI/senha e reset explícito |
| F-06 — N+1 | Eager loading e agregações preexistentes verificados | V3-298–V3-309; consultas constantes com 3/43 usuários; entidades sem tarefas preservadas |
| F-07 — Validação inconsistente | Validadores preexistentes verificados e complementados por C-01 | Tipos, JSON, IDs fora de 64 bits, relações, limites, filtros e Unicode; negativas com estado completo preservado |
| F-08 — Erros dispersos | Fronteira central preexistente com rollback verificada | V3-191–V3-196: triggers em update/exclusão de usuário preservam dados; requisição seguinte atende; logs não expõem marcador interno |
| F-09 — APIs deprecated | Substituições preexistentes verificadas: `session.get()` e `utc_now()` | Busca estática sem `Query.get()`/`datetime.utcnow()` nos fontes; ausência de registros e janela UTC controlada verificadas |
| F-10 — Políticas repetidas | Constantes/regras preexistentes em `services/task_rules.py` verificadas | Limites de título/prioridade; V3-296–V3-297: atraso coerente em lista, estatísticas e relatório |
| F-11 — Código sem consumidor | Remoções preexistentes revisadas: helper antigo, SMTP e imports apontados no legado | Busca estática de referências e boot dos fontes correntes |

As disposições se limitam às ocorrências e contratos auditados. Não equivalem a
uma afirmação de ausência universal de anti-patterns ou vulnerabilidades.

## Consultas e dados

Medições usaram requests isoladas pelo Flask test client, incluindo autenticação:

| Operação | 3 usuários | 43 usuários |
|---|---:|---:|
| `GET /tasks` | 2 SELECTs | 2 SELECTs |
| `GET /users` | 2 SELECTs | 2 SELECTs |
| `GET /categories` | 2 SELECTs | 2 SELECTs |
| `GET /reports/summary` | 5 SELECTs | 5 SELECTs |

Exclusão autorizada de usuário remove tarefas/sessões na mesma unidade de
trabalho; falha injetada preserva os dados. Exclusão de categoria preserva
tarefas e anula `category_id`. Usuários/categorias sem tarefas permanecem nos
resultados, com contagens/taxas zero. Datas controladas verificaram estados
terminais, atraso e janela de sete dias. A migração MD5 e criação de sessão
permanecem na mesma transação.

## Checklist final e limites

- [x] Auditoria aprovada salva antes das alterações; snapshot anterior preservado.
- [x] C-01 reproduzido antes e corrigido com evidência posterior.
- [x] Boot do código corrente e sucesso nas 22 operações.
- [x] Fluxos válidos, entradas inválidas, permissões e efeitos persistidos verificados.
- [x] Senhas, sessões, credenciais legadas longas e ausência de campos sensíveis verificados.
- [x] Rollback, referências, schema legado e seed isolado verificados.
- [x] Versões/hashes registrados nas duas evidências e coincidentes com os fontes finais.
- [x] Banco local preservado e documentação atualizada.
- [x] Achados atuais/legados vinculados às correções e verificações correspondentes.

Não foram medidos cobertura de linhas, carga ou concorrência. As contagens de
consultas não demonstram capacidade sob carga. A revisão de APIs específicas
não equivale a uma varredura universal de warnings. A validação do schema legado
usa uma fixture sintética; o banco local real não foi migrado nem resetado.
Não foi testada integração externa de email, pois ela não integra o fluxo.

Para query strings, bytes de um surrogate percent-encoded podem ser preservados
pelo parser em vez de virar um surrogate Python. A suíte verifica busca válida
com emoji; não a apresenta como prova de rejeição de todo encoding HTTP
inválido. O helper também protege chamadas internas ao filtro `q`.

Evidências finais:

- [Resultados HTTP, invariantes e hashes](evidence/validation-project-3.json).
- [Log do executor HTTP](evidence/validation-project-3.log).
- [Resultados lifecycle, versões e hashes](evidence/validation-project-3-lifecycle.json).
- [Log lifecycle](evidence/validation-project-3-lifecycle.log).
