# ecommerce-api-legacy

LMS de cursos, matrículas e pagamentos simulados, refatorado para MVC com a skill
`refactor-arch`. Express 4 e sqlite3 foram preservados, sem novas dependências.

## Como executar

Requer Node.js e npm; validação executada com Node `24.19.0`, npm `11.17.0`,
Express `4.22.1` e sqlite3 `5.1.7` (SQLite `3.44.2`). Dentro deste diretório:

```bash
npm ci
export ADMIN_API_TOKEN="$(node -p 'require("node:crypto").randomBytes(32).toString("hex")')"
export DEMO_USER_PASSWORD="$(node -p 'require("node:crypto").randomBytes(24).toString("hex")')"
export SEED_DEMO_DATA=1
npm start
```

O servidor usa `http://127.0.0.1:3000`. `HOST` e `PORT` permitem outro endereço e
porta (`PORT=0` escolhe uma porta livre). SIGINT/SIGTERM encerram o servidor e
fecham o banco após as operações em andamento.

O banco permanece **em memória** e perde os dados quando o processo termina.
Sem `SEED_DEMO_DATA=1`, inicia com schema vazio. O modo demonstrativo exige
`DEMO_USER_PASSWORD` não vazia, com até 1024 bytes, e cria dois cursos de preços
997 e 497, um usuário demonstrativo, uma matrícula e um pagamento de 997.
A senha demonstrativa é armazenada como hash; não existe senha padrão no código.
Não há migração de banco persistente nem serviço de pagamento externo.

`ADMIN_API_TOKEN` é uma credencial administrativa: use valor aleatório gerado
externamente, de 32 a 1024 caracteres, sem espaços. Sem essa variável, relatório
e exclusão ficam bloqueados. Os valores gerados acima permanecem no ambiente
do terminal; não os adicione ao repositório ou às evidências.

Em outro terminal, disponibilize o mesmo token para consultar o relatório:

```bash
curl -sS http://127.0.0.1:3000/api/admin/financial-report \
  -H "Authorization: Bearer $ADMIN_API_TOKEN"
```

Exemplos sintéticos de checkout e exclusão estão em [api.http](api.http).

## Contratos HTTP

| Operação | Entrada e comportamento |
|---|---|
| `POST /api/checkout` | JSON com `usr`, `eml`, `pwd`, `c_id`, `card`; sucesso `200 {"msg":"Sucesso","enrollment_id":…}`. |
| `GET /api/admin/financial-report` | Bearer administrativo; `200` com array de `{course,revenue,students:[{student,paid}]}`. Inclui cursos sem alunos; receita soma apenas `PAID`. |
| `DELETE /api/users/:id` | Bearer administrativo; `200` e texto `Usuário deletado` para usuário sem dependências; `409` com matrículas; `404` inexistente; `400` ID inválido. |

No checkout, nome é texto não vazio de até 200 caracteres; email válido tem até
254 caracteres; senha não pode ser vazia ou só espaços e tem até 1024 bytes;
`c_id` é número inteiro positivo seguro; `card` é texto não vazio de até 64
caracteres. Nomes/emails recebem trim, email é único sem distinguir maiúsculas.
Campos extras não definem permissões nem são persistidos.

Conta existente exige a senha correta (`401` se incorreta); senha ausente retorna
`400`. Curso inexistente/inativo retorna `404`. O simulador aprova strings
iniciadas por `4` e recusa as demais com `400`; não valida cartão real e não
armazena nem registra seu conteúdo. Checkout recusado ou com falha intermediária
não deixa usuário, matrícula, pagamento ou auditoria parcial.

Entradas inválidas retornam `400`, payload acima de 16 KiB retorna `413` e formato
de transporte não suportado retorna `415`. Erros internos retornam apenas
`500 Erro interno`, com evento sanitizado no log. Credencial administrativa ausente
ou incorreta retorna `401` com `WWW-Authenticate`.

A exclusão protege o histórico financeiro: não remove usuário matriculado. Como
o checkout cria matrícula, a validação de exclusão bem-sucedida usa uma fixture
isolada de usuário sem dependências.

## Estrutura MVC

```text
src/
  app.js                  # factory, composição e startup npm start
  config.js               # ambiente validado
  database.js             # schema, conexão em memória, fila e transações
  seed.js                 # fixture demonstrativa explícita
  errors.js               # fronteira central de erros
  models/                 # SQL por domínio e relatório em uma consulta
  controllers/            # coordenação de checkout, relatório e exclusão
  services/               # checkout transacional, senhas e simulador
  views/routes.js         # HTTP, Bearer e apresentação JSON explícita
tests/run-validation.js   # validação dos fontes correntes por HTTP real
```

Routes chamam controllers, que coordenam serviços/models. Models e serviços não
dependem de objetos HTTP. Uma fila da conexão abrange cada caso de uso completo;
transações usam `BEGIN IMMEDIATE`, commit/rollback e chaves estrangeiras RESTRICT.
Leituras do relatório aguardam transações, sem observar estados parciais.

## Análise manual e execução da skill

Os cinco problemas documentados no [passo a passo](../PLANO_EXECUCAO.md) foram
confirmados no legado, antes das alterações:

| ID manual | Severidade | Local original | Problema e resultado |
|---|---|---|---|
| P2-01 | CRITICAL | `src/AppManager.js:45` | Cartão/configuração no log; F-01 remove a exposição. |
| P2-02 | MEDIUM | `src/AppManager.js:83–106` | N+1 no relatório; F-06 usa uma consulta. |
| P2-03 | MEDIUM | `src/AppManager.js:29–35,45–46` | Tipos não validados; F-07 retorna 400 sem queda do processo. |
| P2-04 | LOW | `src/AppManager.js:29–33` | Abreviações ambíguas; F-09 usa nomes de domínio e preserva o payload. |
| P2-05 | LOW | `src/utils.js:10,25`, `src/AppManager.js:2` | `totalRevenue` sem uso; F-10 remove código/estado sem consumidor. |

A mesma skill está em [.agents/skills/refactor-arch](.agents/skills/refactor-arch/SKILL.md),
com as cinco referências de análise, catálogo, template, MVC e playbook.
Para outra execução no projeto, invoque `$refactor-arch` e indique o alvo e
destino do relatório. Ela analisa e audita em leitura, apresenta o plano e
aguarda revisão humana antes da Fase 3. A aprovação desta execução foi o `sim`
posterior à apresentação integral da auditoria; a cópia foi salva antes de editar
os fontes. As alterações preexistentes na skill foram preservadas.

## Resultados e validação

```bash
npm test
# Evidências opcionais, partindo deste diretório:
npm test -- --json ../reports/evidence/validation-project-2.json
```

O runner carrega os **fontes correntes**, abre HTTP em loopback/porta efêmera e usa
bancos descartáveis. Não depende do executor histórico preso a um commit.
Credenciais são geradas em memória e snapshots de dados sensíveis não são
exportados. Não exige variáveis de ambiente do usuário.

**34/34 cenários passaram**, incluindo os 14 históricos adaptados e as três
operações originais. Foram conferidos autorização, tipos, senhas, persistência,
exclusão permitida/impedida, rollback em pagamentos/auditoria, recuperação após
erro, concorrência, integridade referencial e logs. O relatório executou uma
consulta com volume pequeno e após adicionar 25 cursos.

A auditoria identificou 10 findings (2 CRITICAL, 3 HIGH, 3 MEDIUM e 2 LOW), todos
relacionados a correções e verificações no relatório de validação. Não há
depreciação confirmada nesta stack. Cobertura de operações não representa
cobertura de linhas, teste de carga ou garantia geral de segurança em produção.

- [Auditoria original](../reports/audit-project-2.md)
- [Baseline histórica](../reports/baseline-project-2.md)
- [Validação e comparação antes/depois](../reports/validation-project-2.md)
- [Evidência JSON](../reports/evidence/validation-project-2.json)
- [Log de validação](../reports/evidence/validation-project-2.log)
