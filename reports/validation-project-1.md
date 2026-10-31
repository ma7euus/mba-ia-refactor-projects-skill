# Validação da refatoração — code-smells-project

A Fase 3 da skill `refactor-arch` foi concluída após o usuário aprovar a [auditoria e o plano](audit-project-1.md) com a resposta “sim”. A auditoria foi salva antes da edição dos fontes e conserva os locais e hashes do legado. Este relatório registra o resultado posterior; não substitui a auditoria.

## Execução e rastreabilidade

- **Data da execução consolidada:** 31/10/2026, aproximadamente 01:25 UTC (30/10/2026, 22:25 America/Sao_Paulo).
- **Fonte validada:** worktree corrente sobre HEAD `7ddd47686a1fc6c6be968b9adf9789ee18ae3ce5`, com os fontes refatorados, sem `git archive`.
- **Ambiente:** Python 3.14.4, SQLite 3.46.1, Flask 3.1.1, flask-cors 5.0.1 e Werkzeug 3.1.9.
- **Comando:** `.venv/bin/python tests/run_validation.py`, dentro de `code-smells-project/`.
- **Servidor:** subprocesso executando o `app.py` corrente, com `HOST=127.0.0.1`, `PORT` temporária, `DATABASE_PATH` em diretório descartável, debug e reloader desativados.
- **Sandbox:** os testes HTTP precisaram de execução com permissão para abrir sockets locais; a execução consolidada autorizada terminou com código 0.
- **Resultado:** **15/15 testes**, zero falhas e zero erros; **155 verificações HTTP registradas**, **39 cenários históricos adaptados** e **19/19 operações exercitadas com sucesso autorizado**. A comparação com `app.url_map` também passou.
- **Evidências:** [JSON sanitizado](evidence/validation-project-1.json), com resultados, versões e SHA-256 dos fontes/testes; [log de boot e unittest](evidence/validation-project-1.log).
- **Código do executor:** [tests/run_validation.py](../code-smells-project/tests/run_validation.py).

A primeira rodada de integração encontrou duas divergências de status entre os testes e a implementação. O cadastro com papel indevido foi corrigido para `400`, conforme o plano; uma violação de integridade SQLite mantém `409`, e o teste passou a verificar esse contrato preservando as verificações de rollback. A revisão também corrigiu validação de IDs antes de autorização/binding, compatibilidade de senhas legadas longas, migração com colunas reordenadas e estouro numérico no agregado do relatório. A execução consolidada acima ocorreu depois de todas essas correções.

## Estrutura e responsabilidades

Antes: quatro arquivos Python, 780 linhas físicas; configuração e administração em `app.py`, regras e SQL distribuídos entre `controllers.py`, `models.py` e `database.py`.

Depois: 28 arquivos Python de aplicação, 1.249 linhas físicas, incluindo módulos de pacote, comentários e linhas vazias. Testes, skill, dependências, caches e evidências estão excluídos dessa contagem. O aumento inclui a migração explícita, provisionamento local e verificações de segurança/integridade.

```text
code-smells-project/
  app.py
  src/
    __init__.py           # factory e construção/injeção das dependências
    config.py             # ambiente e localização do banco
    database.py           # conexão por contexto, transações, schema e migração
    cli.py                # init-db, migrate-db, create-admin, set-password
    errors.py             # fronteira sanitizada de erros
    validation.py         # tipos, faixas e invariantes
    models/               # SQL parametrizado por domínio
    services/             # regras, pedidos, relatórios e administração
    controllers/          # coordenação sem objetos HTTP
    views/                # rotas, HTTP Basic e serializers explícitos
  tests/run_validation.py
```

Os módulos antigos foram substituídos pelos componentes correspondentes; não restaram cópias executáveis dos handlers vulneráveis. Os models recebem conexão explicitamente. SQL não aparece nos controllers ou nas views; pedidos usam uma transação com `BEGIN IMMEDIATE`, baixa condicionada de estoque e rollback. Notificações continuam simuladas e são registradas depois do commit.

## Disposição dos findings

| Finding | Estado | Implementação | Verificação executada |
|---|---|---|---|
| F-01 / AP-01 — SQL concatenado | Corrigido | `src/models/{products,users,orders}.py`; whitelist em `models/system.py` | Nome com apóstrofo criado com 201; login com texto SQL recusado com 401; consulta arbitrária recusada com 400 |
| F-02 / AP-02 — Dados sensíveis | Corrigido | `views/serializers.py`, `models/system.py`, configuração e launcher | Respostas HTTP percorridas recursivamente sem senha/hash/segredo/path; health sem configuração interna |
| F-03 / AP-13 — Autorização | Corrigido | `views/auth.py`, `controllers/orders.py`, `services/admin.py`, `cli.py` | Anônimo/credencial inválida 401, cliente sem papel/propriedade 403, proprietário/admin permitidos; admin/query e reset exercitados também no fluxo permitido |
| F-04 / AP-05 — Senha textual | Corrigido | `models/users.py`, `services/users.py`, `database.py`, `cli.py` | Hash verificado com Werkzeug; migração mantém login, inclusive senha legada longa; repetição não refaz hash; admin de demonstração bloqueado até redefinição |
| F-05 / AP-06 — Conexão global | Corrigido | `database.get_db`, `init_app` e `transaction` | Requisições HTTP independentes, rollback seguido de sucesso e duas requisições concorrentes disputando o último item |
| F-06 / AP-14 — Integridade | Corrigido | FKs/restrições em `database.py`; `models/products.py`; `services/orders.py` | Usuário inexistente 404 sem mutação; produto referenciado 409; falha no segundo item reverte tudo; `foreign_key_check` vazio |
| F-07 / AP-08 — Validação | Corrigido | `validation.py`, serviços e validação de IDs nas views | Tipos/faixas/JSON inválidos 400 sem alteração; quantidade negativa/zero/fracionária e soma duplicada recusadas; status inexistente 404; IDs acima do limite SQLite não geram 500 |
| F-08 / AP-04 — Camadas misturadas | Corrigido | Factory, models, serviços, controllers e views separados | Revisão das dependências; testes de domínio/migração sem servidor e de todos os fluxos via HTTP |
| F-09 / AP-07 — N+1 | Corrigido | `models/orders.py` usa um JOIN | Consultas contadas para 1 e 20 pedidos: crescimento limitado; itens e nomes preservados |
| F-10 / AP-10 — Erros/logs | Corrigido | `errors.py` e logging dos serviços | JSON malformado 400; conflito sanitizado 409; falha inesperada controlada 500 sem dados sensíveis na resposta ou nos logs |
| F-11 / AP-12 — Valores sem nomes | Corrigido | `services/reports.py`, `DISCOUNT_TIERS` | Limiares estritos verificados abaixo, no valor e acima de 1.000, 5.000 e 10.000; arredondamento preservado |

Os 11 findings possuem correção e evidência dentro da cobertura descrita. Isso não representa uma afirmação de ausência universal de problemas na aplicação.

## Antes e depois

| Comportamento | Baseline legada | Código corrente |
|---|---|---|
| Health/usuários | Segredo e senhas no JSON | Apenas campos públicos |
| Armazenamento de senha | Texto puro | Hash scrypt, verificação e migração explícitas |
| Preço textual/filtro inválido | 500 | 400 |
| Produto com apóstrofo | 500 | 201, entrada tratada como dado |
| Pedido com quantidade negativa | 201, total negativo e estoque aumentado | 400, registros e campos preservados |
| Pedido para usuário inexistente | 201, relação órfã | 404, sem gravação |
| Status de pedido inexistente | 200 | 404 |
| Consulta administrativa anônima | 200 | 401 |
| SQL administrativo arbitrário | Executável | 400, apenas quatro contagens internas permitidas |
| Reset anônimo | 200 e exclusão dos dados | 401, sem mutação |
| Reset autorizado em banco descartável | Sem controles | 200 somente com papel, duas flags e confirmação; tabelas vazias sem seed automático |
| Produto referenciado por pedido | Exclusão física sem política | 409 |
| Banco no import/boot | Inicialização/seed automáticos no boot | Nenhum arquivo criado; health 503 se banco ausente ou legado |

Exemplos de persistência confirmados pelas assertions SQL: produto editado com nome `Produto Editado`, preço `27.5` e estoque `15`; pedido de duas unidades com total `179.8`, quantidade `2` e estoque reduzido de `50` para `48`; status `aprovado` persistido; relatório completo correspondente ao pedido aprovado. As recusas comparam snapshots de **todos os campos e registros** das quatro tabelas, não somente contagens.

## Continuidade das operações

Todas as linhas abaixo tiveram execução HTTP bem-sucedida com entrada válida e, quando necessário, credenciais autorizadas. Rotas de recurso inexistente foram verificadas separadamente.

| Método | Rota | Status válido |
|---|---|---:|
| GET | `/` | 200 |
| GET | `/health` | 200 |
| GET | `/produtos` | 200 |
| GET | `/produtos/busca` | 200 |
| GET | `/produtos/<int:id>` | 200 |
| POST | `/produtos` | 201 |
| PUT | `/produtos/<int:id>` | 200 |
| DELETE | `/produtos/<int:id>` | 200 |
| GET | `/usuarios` | 200 |
| GET | `/usuarios/<int:id>` | 200 |
| POST | `/usuarios` | 201 |
| POST | `/login` | 200 |
| POST | `/pedidos` | 201 |
| GET | `/pedidos` | 200 |
| GET | `/pedidos/usuario/<int:usuario_id>` | 200 |
| PUT | `/pedidos/<int:pedido_id>/status` | 200 |
| GET | `/relatorios/vendas` | 200 |
| POST | `/admin/query` | 200 |
| POST | `/admin/reset-db` | 200 |

## Dados preservados e limites

O `code-smells-project/loja.db` local não foi migrado, populado ou usado nos testes. SHA-256 antes e depois:

```text
580f493b6c81905b618c3234453c87a44b70d2e0ec6ae048e0b6247959045c73
```

A migração foi executada em fixtures descartáveis que reproduzem o schema legado. Verificou preservação de IDs, timestamps, relações, sequência de IDs, login e valores com colunas físicas reordenadas; rejeição de órfãos sem alteração; e rollback completo diante de falha durante a conversão de senhas.

Para usar o banco local legado com a aplicação nova, ainda é necessário executar **explicitamente** `migrate-db` e redefinir a senha do administrador de demonstração. Os comandos estão no [README do projeto](../code-smells-project/README.md). Nenhuma correção destrutiva de dados locais foi realizada.

A política aprovada mantém pedidos cancelados no relatório e não implementa restituição de estoque no cancelamento. Não há integrações reais de email/SMS/push. Não foram realizados testes de carga ou avaliação exaustiva de segurança; a medição de operações não equivale a cobertura de linhas.

As alterações preexistentes na skill foram preservadas. Nenhum projeto vizinho foi refatorado. Não houve commit, push ou publicação.
