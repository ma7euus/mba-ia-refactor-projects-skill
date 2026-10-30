# Baseline — ecommerce-api-legacy

- **Commit-base:** `6d1ce6248c3e956801010a89d8bdaab48029bf30`.
- **Execução (UTC):** 2026-10-30T02:09:49.741462+00:00.
- **Ambiente observado:** `{"node": "v24.19.0", "express": "4.22.1", "sqlite3": "5.1.7"}`.
- **Isolamento:** cópia do commit-base em diretório temporário; banco descartável; bancos locais preservados.
- **HTTP:** servidor real em loopback e porta efêmera. Flask executa o entry point por `runpy`, com debug e reloader desativados. Node carrega o entry point por `require`, com observador SQLite que aceita somente SELECT.
- **Código da aplicação preservado na execução:** sim.
- **Cobertura de operações:** 3/3 combinações método/rota.
- **Cenários:** 14; **cenários com desvios:** 6.

As expectativas representam o comportamento correto desejado. Um desvio documenta uma falha observada do legado; não é resultado a perpetuar na refatoração. Esta baseline não é o relatório da Fase 2 da skill.

Requisições, respostas completas sanitizadas, verificações e contagens de tabelas: [evidência JSON](evidence/baseline-project-2.json). Boot, avisos e erros: [log sanitizado](evidence/baseline-project-2.log).

## Operações inventariadas

| Método | Rota | Exercitada |
|---|---|---|
| DELETE | `/api/users/:id` | Sim |
| GET | `/api/admin/financial-report` | Sim |
| POST | `/api/checkout` | Sim |

## Baseline por método e rota

Uma linha por cenário executado, identificado pelo ID e pelo nome na primeira coluna. Valores sensíveis permanecem mascarados. Contagens sem variação não comprovam ausência de updates; os checks de persistência informam os valores observados. A indicação de preservar se limita às verificações deste cenário.

| Método e rota | Entrada | Status observado | Campos relevantes da resposta | Efeito no banco | Comportamento correto a preservar ou falha a corrigir |
|---|---|---|---|---|---|
| `GET /api/admin/financial-report`<br>**P2-01** — Relatório financeiro com os dados iniciais | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 200 | Lista com 2 item(ns); campos: `course, revenue, students`. revenue=997 | Contagens das tabelas sem variação. | Preservar: Dois cursos; receita inicial total de 997 e uma matrícula paga. |
| `POST /api/checkout`<br>**P2-02** — Checkout aprovado de usuário novo | JSON: `{"usr":"Baseline Paid Student","eml":"baseline-paid@example.test","c_id":1,"card":"[MASCARADO]","pwd":"[MASCARADO]"}` | 200 | `msg="Sucesso"`; `enrollment_id=2` | Contagens: `audit_logs`: 0 → 1; `enrollments`: 1 → 2; `payments`: 1 → 2; `users`: 1 → 2. Check de persistência «Pagamento persistido»: observado `[{"amount":997,"status":"PAID"}]`. | Preservar: Cria usuário, matrícula, pagamento PAID e registro de auditoria. |
| `GET /api/admin/financial-report`<br>**P2-03** — Relatório após checkout aprovado | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 200 | Lista com 2 item(ns); campos: `course, revenue, students`. revenue=1994 | Contagens das tabelas sem variação. | Preservar: Receita total de 1994 e inclusão do aluno sintético. |
| `POST /api/checkout`<br>**P2-04** — Checkout de usuário já cadastrado em outro curso | JSON: `{"usr":"Baseline Paid Student","eml":"baseline-paid@example.test","c_id":2,"card":"[MASCARADO]","pwd":"[MASCARADO]"}` | 200 | `msg="Sucesso"`; `enrollment_id=3` | Contagens: `audit_logs`: 1 → 2; `enrollments`: 2 → 3; `payments`: 2 → 3. Check de persistência «Usuário não duplicado»: observado `0`. | Preservar: Reutiliza o usuário e adiciona matrícula e pagamento de 497. |
| `POST /api/checkout`<br>**P2-05** — Checkout com pagamento recusado | JSON: `{"usr":"Baseline Denied Student","eml":"baseline-denied@example.test","c_id":1,"card":"[MASCARADO]","pwd":"[MASCARADO]"}` | 400 | Texto: `"Pagamento recusado"` | Contagens: `users`: 2 → 3. Efeito legado observado: variação de usuários = 1; criação ocorre antes da recusa. | Preservar HTTP 400 sem matrícula/pagamento; revisar a criação do usuário antes da recusa, observada no legado. |
| `POST /api/checkout`<br>**P2-06** — Checkout sem campos obrigatórios | JSON: `{"usr":"Baseline Missing Fields"}` | 400 | Texto: `"Bad Request"` | Contagens das tabelas sem variação. | Preservar: Rejeita entrada incompleta sem persistir registros. |
| `POST /api/checkout`<br>**P2-07** — Checkout com curso inexistente | JSON: `{"usr":"Baseline Unknown Course","eml":"baseline-unknown@example.test","c_id":999999,"card":"[MASCARADO]","pwd":"[MASCARADO]"}` | 404 | Texto: `"Curso não encontrado"` | Contagens das tabelas sem variação. | Preservar: Curso inexistente deve retornar 404 sem gravações. |
| `POST /api/checkout`<br>**P2-08** — Checkout de usuário novo sem senha | JSON: `{"usr":"Baseline No Password","eml":"baseline-no-password@example.test","c_id":2,"card":"[MASCARADO]"}` | 200 | `msg="Sucesso"`; `enrollment_id=4` | Contagens: `audit_logs`: 2 → 3; `enrollments`: 3 → 4; `payments`: 3 → 4; `users`: 3 → 4. Variações observadas: usuários=1, matrículas=1, pagamentos=1. | Validar o cadastro e retornar 400; o legado aceita a ausência de senha e usa um valor padrão. |
| `POST /api/checkout`<br>**P2-09** — Checkout com email malformado | JSON: `{"usr":"Baseline Invalid Email","eml":"invalid-email-baseline","c_id":2,"card":"[MASCARADO]","pwd":"[MASCARADO]"}` | 200 | `msg="Sucesso"`; `enrollment_id=5` | Contagens: `audit_logs`: 3 → 4; `enrollments`: 4 → 5; `payments`: 4 → 5; `users`: 4 → 5. Check de persistência «Nenhum usuário com email inválido persistido»: observado `[{"total":1}]` (divergente do esperado). | Rejeitar email inválido com 400 antes de persistir usuário ou matrícula. |
| `GET /api/admin/financial-report`<br>**P2-10** — Relatório administrativo sem autenticação | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 200 | Lista com 2 item(ns); campos: `course, revenue, students`. revenue=3485 | Contagens das tabelas sem variação. | Exigir autenticação/autorização administrativa, com 401/403 para a chamada anônima. |
| `DELETE /api/users/2`<br>**P2-11** — Exclusão de usuário sintético com matrículas | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 200 | Texto: `"Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."` | Contagens: `users`: 5 → 4. Check de persistência «Usuário removido»: observado `[{"total":0}]`. Check de persistência «Nenhuma matrícula órfã»: observado `[{"total":2}]` (divergente do esperado). | Preservar integridade referencial ao excluir ou rejeitar a operação; o legado deixou duas matrículas órfãs. |
| `GET /api/admin/financial-report`<br>**P2-12** — Relatório após exclusão de usuário matriculado | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 200 | Lista com 2 item(ns); campos: `course, revenue, students`. revenue=3485 | Contagens das tabelas sem variação. Receita antes/depois da exclusão: 3485 / 3485; alunos apresentados como Unknown: 2. | Preservar: Relatório permanece acessível; observar o efeito da exclusão nas matrículas e receita. |
| `DELETE /api/users/999999`<br>**P2-13** — Exclusão de usuário inexistente | Sem payload nem query; parâmetros, quando presentes, constam no caminho. | 200 | Texto: `"Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."` | Contagens das tabelas sem variação. | Retornar 404 em vez de alegar exclusão de um registro inexistente. |
| `POST /api/checkout`<br>**P2-14** — Checkout com card numérico | JSON: `{"usr":"Baseline Numeric Card","eml":"baseline-numeric@example.test","c_id":1,"card":"[MASCARADO]","pwd":"[MASCARADO]"}`<br>`card` era numérico; valor mascarado na evidência | Sem resposta HTTP | Falha de transporte: RemoteDisconnected | Observação do banco indisponível após a falha do processo; não foi possível confirmar o estado posterior. | Validar o tipo e retornar 400; o legado encerrou o processo sem resposta HTTP. |

## Desvios observados

- **P2-08 — Checkout de usuário novo sem senha:** HTTP 200; Cadastro sem senha deve ser rejeitado; o legado usa uma senha padrão.
- **P2-09 — Checkout com email malformado:** HTTP 200; Email malformado deve ser rejeitado antes do cadastro; verificações reprovadas: Nenhum usuário com email inválido persistido.
- **P2-10 — Relatório administrativo sem autenticação:** HTTP 200; Dados administrativos devem exigir autenticação/autorização.
- **P2-11 — Exclusão de usuário sintético com matrículas:** HTTP 200; Excluir usuário deve preservar integridade referencial ou rejeitar a operação; verificações reprovadas: Nenhuma matrícula órfã.
- **P2-13 — Exclusão de usuário inexistente:** HTTP 200; Um usuário inexistente deve ser identificado sem alegar exclusão bem-sucedida.
- **P2-14 — Checkout com card numérico:** sem resposta HTTP; Tipo inválido deve retornar 400 sem encerrar o processo; verificações reprovadas: Sem TypeError no processo.

## Observações de comportamento

- O relatório financeiro é acessível sem autenticação/autorização.
- O checkout aceita cadastro sem senha e email malformado.
- A exclusão deixa matrículas e pagamentos ligados a usuário removido; o relatório usa Unknown.
- A exclusão de usuário inexistente responde sucesso.
- O checkout recusado cria o usuário antes de negar o pagamento; esse efeito deve ser considerado na decisão de atomicidade.
- Card numérico provoca TypeError em startsWith e pode encerrar o processo em vez de retornar 400.
- O log do checkout contém cartão sintético e chave de configuração; a evidência persistida deve mascarar ambos.

## Reprodução e limites

```bash
python3 scripts/baseline/run.py --project 2
```

Usa as dependências já instaladas em `.venv` de cada Flask e `node_modules` do LMS. A fonte é sempre o commit-base, não o código corrente. A configuração de rede/debug e a instrumentação pertencem ao executor, sem editar os fontes legados.

- Pagamento é simulado localmente pelo prefixo do campo card; não houve gateway, cartão real, SMTP nem serviço externo. SELECTs de observação usam o mesmo SQLite em memória do processo, sem alterar os dados.
- A cobertura mede operações exercitadas, não cobertura de linhas, carga ou todos os caminhos possíveis.
- Dados sensíveis são mascarados nas evidências. IDs, timestamps, portas e datas relativas do seed podem variar entre execuções.
