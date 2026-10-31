# code-smells-project

API de loja em Python/Flask refatorada para MVC com a skill `refactor-arch`. Mantém as 19 operações do legado, com as correções de segurança e integridade aprovadas na [auditoria](../reports/audit-project-1.md). A [validação](../reports/validation-project-1.md) registra os resultados contra o código corrente.

## Preparar e executar

Execute os comandos dentro de `code-smells-project/`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export DATABASE_PATH="$PWD/loja.db"
```

Para um **banco novo**, crie o schema vazio e provisione o administrador. A senha será solicitada sem eco no terminal:

```bash
.venv/bin/flask --app app init-db
.venv/bin/flask --app app create-admin --nome Administrador --email admin@example.test
.venv/bin/python app.py
```

A aplicação escuta em `http://127.0.0.1:5000`, com debug e reloader desativados. Importar ou iniciar a aplicação não cria tabelas, usuários ou produtos. `GET /` funciona sem banco; operações que precisam de banco retornam `503` se faltar inicialização ou migração.

### Banco legado existente

O banco local foi preservado durante a refatoração e os testes. Para usá-lo, faça uma cópia de segurança com a aplicação parada e execute explicitamente:

```bash
.venv/bin/flask --app app migrate-db
.venv/bin/flask --app app set-password --email admin@loja.com
```

A migração converte senhas textuais em hashes scrypt do Werkzeug, mantém IDs, timestamps, registros e sequências, e acrescenta restrições relacionais. A versão do schema identifica a migração; repetir o comando não recalcula hashes. O administrador legado de demonstração fica desativado até a redefinição local da senha.

Órfãos, emails duplicados, objetos personalizados ou dados incompatíveis impedem a migração, que reverte as mudanças. Revise esses dados antes de tentar novamente; o comando não os exclui ou corrige silenciosamente. `init-db` recusa sobrescrever um banco legado.

## Autenticação e contratos

As operações protegidas usam **HTTP Basic**. Email e senha são verificados a cada requisição; o papel é carregado do banco. Use HTTPS quando disponibilizar a API fora do ambiente local. `/login` mantém o JSON do legado e verifica credenciais; não emite token ou sessão.

| Acesso | Operações |
|---|---|
| Público | `GET /`, `GET /health`, leitura/busca de produtos, `POST /usuarios`, `POST /login` |
| Administrador | Escrita/exclusão de produtos, listagem de usuários, listagem geral de pedidos, atualização de status, relatório e administração |
| Próprio usuário ou administrador | Detalhe de usuário, pedidos de um usuário e criação de pedido para esse usuário |

Cadastro público cria apenas clientes; enviar outro `tipo` retorna `400`. Credenciais ausentes/incorretas retornam `401`; falta de permissão retorna `403`. Senhas, hashes e configuração interna não aparecem nas respostas. Não há credenciais ou dados de exemplo criados automaticamente.

Exemplo de operação protegida, com senha solicitada pelo curl:

```bash
curl -u admin@example.test http://127.0.0.1:5000/usuarios
curl -u admin@example.test -H 'Content-Type: application/json' \
  -d '{"nome":"Caderno","descricao":"Pautado","preco":25,"estoque":12,"categoria":"geral"}' \
  http://127.0.0.1:5000/produtos
```

Os campos e respostas válidos do legado foram preservados. As mudanças intencionais incluem autorização, remoção de campos sensíveis, `400` para tipos/faixas inválidos, `404` para pedido/usuário inexistente e `409` ao excluir produto referenciado. Quantidades precisam ser inteiros positivos; produtos repetidos têm quantidades agregadas. Pedido, itens e estoque são gravados na mesma transação. Status de cancelamento preserva o comportamento anterior e **não repõe estoque**. O relatório mantém a política anterior, incluindo pedidos cancelados na soma e os limiares estritos de desconto.

### Administração limitada

`POST /admin/query` aceita somente quatro consultas predefinidas, uma por tabela, com o campo `sql` neste formato:

```json
{"sql":"SELECT COUNT(*) AS total FROM produtos"}
```

As tabelas permitidas são `produtos`, `usuarios`, `pedidos` e `itens_pedido`. Maiúsculas, espaços e ponto e vírgula final são normalizados; a execução usa SQL interno fixo. Qualquer outra consulta retorna `400`.

`POST /admin/reset-db` exige administrador, `ENABLE_DB_RESET=true`, `DISPOSABLE_DATABASE=true` e JSON `{"confirmacao":"RESET"}`. Use essas opções somente para um banco descartável configurado explicitamente por `DATABASE_PATH`. O reset autorizado apaga as quatro tabelas em uma transação, inclusive usuários; não executa seed depois. Um administrador pode ser provisionado novamente pelo comando local.

## Organização MVC

```text
app.py                 # launcher estável
src/
  __init__.py          # factory e composição das dependências
  config.py            # ambiente
  database.py          # ciclo de vida, schema e migração
  cli.py               # preparação e provisionamento explícitos
  errors.py            # erros HTTP sanitizados
  validation.py        # tipos e invariantes
  models/              # SQL parametrizado por domínio
  services/            # regras e transações
  controllers/         # coordenação dos casos de uso
  views/               # rotas, autenticação e serializers JSON
```

Models, serviços e controllers recebem dependências explícitas. O acesso a objetos Flask fica na composição, no ciclo de vida da conexão e na adaptação HTTP. As notificações de pedidos continuam simuladas por logging, após o commit.

Configuração: `DATABASE_PATH` (padrão `loja.db` relativo ao diretório de execução), `HOST` (padrão `127.0.0.1`), `PORT` (padrão `5000`), `ENABLE_DB_RESET` e `DISPOSABLE_DATABASE` (ambos falsos por padrão). Não é necessária chave de sessão, pois não há sessão ou token assinado.

## Validação

```bash
.venv/bin/python tests/run_validation.py
```

A suíte inicia o `app.py` corrente em HTTP real, em loopback e porta temporária, e usa bancos descartáveis em `/tmp`. Precisa de permissão para abrir sockets locais. Reexecuta os 39 cenários da baseline com as correções aprovadas e acrescenta permissões, entradas inválidas, concorrência, rollback, migração, consultas em lote e limites de desconto. A saída JSON é sanitizada; o progresso unittest vai para stderr. Nenhum teste usa o banco local.

O executor `../scripts/baseline/run.py` continua medindo o commit legado e não deve ser usado como evidência do código refatorado.
