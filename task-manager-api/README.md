# task-manager-api

API Flask de usuários, tarefas, categorias e relatórios, refatorada para MVC.

## Preparação e execução

Dentro de `task-manager-api/`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m flask --app app init-db
.venv/bin/python app.py
```

O servidor usa `http://127.0.0.1:5000`, com debug desabilitado. Importar `app`
não cria tabelas nem popula dados. `init-db` cria somente tabelas ausentes,
incluindo `auth_sessions`; não apaga ou recria tabelas existentes.

O banco padrão continua sendo **`instance/tasks.db`**, relativo ao projeto,
independentemente do diretório de execução. Para um banco separado, exporte
`DATABASE_URL=sqlite:////caminho/absoluto/tasks.db` antes de executar os comandos.
`HOST`, `PORT`, `FLASK_DEBUG` e `CORS_ORIGINS` também são configuráveis por
ambiente. `CORS_ORIGINS` aceita origens separadas por vírgula. Não existe uma
chave secreta compartilhada embutida; os tokens são aleatórios e verificados
contra sessões persistidas no servidor.

## Administrador e autenticação

Depois de inicializar o schema, crie uma conta administrativa por comando local:

```bash
export ADMIN_NAME='Administrador'
export ADMIN_EMAIL='admin@example.test'
read -rsp 'Senha administrativa: ' ADMIN_PASSWORD
export ADMIN_PASSWORD
.venv/bin/python -m flask --app app create-admin
unset ADMIN_PASSWORD
```

Esse comando cria uma conta nova. Se o email já existir, ele falha sem alterar
ou promover a conta. Não há senha administrativa padrão nem promoção pelo
cadastro público.

`POST /users` aceita `name`, `email` e `password`, com cadastro restrito ao papel
`user`. Nome tem de 1 a 100 caracteres; email tem no máximo 150; novas senhas
têm de 4 a 1.024 caracteres. Solicitar `admin`, `manager` ou definir `active`
no cadastro público retorna `403`.

Faça `POST /login` com email e senha. A resposta mantém `message`, `user` e
`token`; envie o token nas requisições seguintes:

```text
Authorization: Bearer <token recebido no login>
```

Tokens expiram em uma hora. O banco guarda apenas SHA-256 do token aleatório;
o valor original é retornado exclusivamente no login. A identidade, o papel e
o estado ativo são conferidos no servidor em cada requisição. Alterar a senha
revoga todas as sessões da conta. Usuários inativos recebem `403`.

Senhas novas usam scrypt por meio do Werkzeug, com salt aleatório. Contas com
MD5 legado continuam autenticando: somente um login correto de uma conta ativa
converte a senha para o formato atual, na mesma transação que cria a sessão.
Nenhuma resposta pública contém senha ou hash.

## Rotas e permissões

| Operações | Acesso |
|---|---|
| `GET /`, `GET /health` | Público |
| `POST /users`, `POST /login` | Público, com validação |
| `GET /users` | Administrador |
| `GET /users/<id>`, `PUT /users/<id>` | Próprio usuário ou administrador |
| `DELETE /users/<id>` | Administrador; remove usuário, sessões e tarefas na mesma transação |
| `GET /users/<id>/tasks` | Próprio usuário ou administrador |
| `GET /tasks`, `GET /tasks/search`, `GET /tasks/stats` | Autenticado; administrador vê todas, demais veem suas próprias tarefas |
| `POST /tasks` | Autenticado; usuário comum cria para si; administrador pode atribuir ou deixar sem responsável |
| `GET /tasks/<id>`, `PUT /tasks/<id>`, `DELETE /tasks/<id>` | Responsável ou administrador; tarefas sem responsável são administrativas |
| `GET /reports/summary` | Administrador |
| `GET /reports/user/<id>` | Próprio usuário ou administrador |
| `GET /categories` | Autenticado; categorias e contagens são compartilhadas |
| `POST /categories`, `PUT /categories/<id>`, `DELETE /categories/<id>` | Administrador |

Somente administrador altera `role` e `active`. O papel `manager` tem as mesmas
permissões de recursos próprios de `user`. A ausência de credencial ou token
inválido/expirado retorna `401`; falta de permissão retorna `403`. Recursos
inexistentes retornam `404` para quem pode consultar a operação.

Tarefas mantêm os campos públicos originais. Título: 3–200 caracteres;
prioridade inteira: 1–5 (padrão 3); estados: `pending`, `in_progress`, `done`,
`cancelled`; datas: `YYYY-MM-DD`; tags: texto CSV ou lista de textos, com até
500 caracteres após conversão. IDs devem caber em um inteiro positivo de 64 bits.
As buscas aceitam `q`, `status`, `priority` e `user_id`; usuários comuns não podem
filtrar tarefas de outra conta. Entradas inválidas retornam `400` sem gravações.
Cor de categoria usa `#RRGGBB`. A exclusão de uma categoria preserva suas
tarefas, deixando `category_id=null`.

Textos com caracteres Unicode inválidos, como surrogates isolados em JSON,
retornam `400` antes de hashing ou persistência. Acentos e emojis válidos são
preservados; senhas não são normalizadas nem truncadas. O login mantém suporte
a credenciais legadas válidas que excedem os limites atuais de cadastro.

Datas históricas continuam como UTC sem timezone nas colunas SQLite e nos
campos JSON. Atraso exclui tarefas concluídas e canceladas. Relatórios mantêm
os cálculos e campos anteriores, incluindo entidades sem tarefas.

## Dados demonstrativos isolados

Seed é opcional. Para criar 3 usuários, 4 categorias e 10 tarefas em um banco
**descartável**, informe a URI explicitamente e uma senha externa:

```bash
export DATABASE_URL="sqlite:////tmp/task-manager-demo-$(date +%s).db"
read -rsp 'Senha das contas demonstrativas: ' SEED_PASSWORD
export SEED_PASSWORD
.venv/bin/python seed.py --database "$DATABASE_URL"
unset SEED_PASSWORD
.venv/bin/python app.py
```

O seed recusa banco já populado. `--reset` autoriza apagar os dados da URI
explicitamente escolhida; use somente em banco descartável. Reset e população
ocorrem em uma transação. O administrador demonstrativo usa
`joao@email.com`; todos os usuários do seed recebem a senha fornecida. Seeds
não são executados no boot. O serviço SMTP sem consumidores foi removido;
nenhum email é enviado.

## Organização e validação

`app.py` compõe dependências; `routes/` adapta HTTP; `controllers/` coordena casos
de uso; `models/*_repository.py` concentra consultas; `services/` contém regras
e autenticação; `views/` controla autorização HTTP e campos públicos. A sessão
SQLAlchemy permanece vinculada ao contexto Flask. Erros são traduzidos em
`errors.py`, com rollback e mensagens sanitizadas.

```bash
.venv/bin/python tests/run_validation.py --output ../reports/evidence/validation-project-3.json
.venv/bin/python tests/check_lifecycle.py --output ../reports/evidence/validation-project-3-lifecycle.json
```

A validação usa os fontes correntes, servidor HTTP em loopback e bancos
temporários, cobrindo as 22 operações e regressões de segurança, persistência,
rollback e crescimento de consultas. Não altera `instance/tasks.db`.

A [auditoria legada](../reports/audit-project-3.md) preserva os achados originais.
A [auditoria dos fontes atuais](../reports/audit-project-3-current.md) registra
a revisão aprovada antes da correção de Unicode. Resultados observados e limitações ficam no
[relatório de validação](../reports/validation-project-3.md). A
[baseline histórica](../reports/baseline-project-3.md) permanece separada.
