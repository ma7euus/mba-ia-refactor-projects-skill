"""Tabelas de baseline derivadas das evidências, sem executar as aplicações."""

import json
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlsplit


HEADER = (
    "| Método e rota | Entrada | Status observado | Campos relevantes da resposta | "
    "Efeito no banco | Comportamento correto a preservar ou falha a corrigir |"
)

CORRECTIONS = {
    "Health e estado inicial do banco": "Preservar o health; corrigir a exposição de secret_key.",
    "Filtro de preço com tipo inválido": "Corrigir a conversão inválida: retornar 400 em vez de 500.",
    "Listagem de usuários": "Preservar a listagem; remover senhas da resposta.",
    "Detalhe de usuário existente": "Preservar o detalhe; remover a senha da resposta.",
    "Criação de usuário de teste": "Preservar cadastro com 201; substituir armazenamento da senha em texto puro.",
    "Produto com preço textual": "Validar o tipo de preco e retornar 400 em vez de 500.",
    "Produto com apóstrofo no nome": "Aceitar o nome como dado e retornar 201; corrigir a montagem de SQL por concatenação.",
    "Atualização de pedido inexistente": "Retornar 404 em vez de informar sucesso para um pedido inexistente.",
    "Pedido com quantidade negativa": "Rejeitar com 400 sem criar pedido nem aumentar estoque; o legado retorna 201 e total negativo.",
    "Pedido para usuário inexistente": "Rejeitar a relação inválida com 400/404, sem persistir pedido órfão.",
    "Consulta administrativa sem autorização": "Exigir autenticação/autorização e restringir a execução de SQL; a consulta foi aceita anonimamente.",
    "Reset administrativo sem autorização (último cenário)": "Negar operação anônima com 401/403; o legado apagou os dados do banco descartável.",
    "Checkout de usuário novo sem senha": "Validar o cadastro e retornar 400; o legado aceita a ausência de senha e usa um valor padrão.",
    "Checkout com email malformado": "Rejeitar email inválido com 400 antes de persistir usuário ou matrícula.",
    "Relatório administrativo sem autenticação": "Exigir autenticação/autorização administrativa, com 401/403 para a chamada anônima.",
    "Exclusão de usuário sintético com matrículas": "Preservar integridade referencial ao excluir ou rejeitar a operação; o legado deixou duas matrículas órfãs.",
    "Exclusão de usuário inexistente": "Retornar 404 em vez de alegar exclusão de um registro inexistente.",
    "Checkout com card numérico": "Validar o tipo e retornar 400; o legado encerrou o processo sem resposta HTTP.",
    "Detalhe do usuário seed sem autenticação": "Exigir autorização e omitir password/hash; o legado respondeu 200 com o campo sensível.",
    "Criar usuário sintético": "Preservar cadastro com 201; omitir password da resposta e substituir MD5 para armazenamento de senha.",
    "Login válido do usuário sintético": "Preservar autenticação válida; omitir hash da resposta e substituir o token literal previsível.",
    "Editar nome de usuário": "Preservar a atualização do nome; omitir password/hash da resposta.",
    "Task com prioridade textual": "Validar priority e retornar 400 em vez de 500.",
    "Task com título numérico": "Validar title e retornar 400 em vez de 500.",
    "Busca com prioridade inválida": "Validar o filtro priority e retornar 400 em vez de 500.",
    "Busca com usuário inválido": "Validar o filtro user_id e retornar 400 em vez de 500.",
    "Inativar usuário sintético": "Preservar a inativação; omitir password/hash da resposta.",
    "Reativar usuário sintético": "Preservar a reativação; omitir password/hash da resposta.",
    "Cliente promove usuário a admin sem autorização": "Negar promoção anônima com 401/403, preservar a role e omitir password/hash da resposta.",
    "Cadastro solicita role administrativa": "Não conceder role administrativa enviada pelo cliente; negar/restringir a solicitação e omitir password/hash.",
}


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", "<br>")


def deviates(case):
    expected = case["expected_status"]
    allowed = expected if isinstance(expected, (list, tuple)) else [expected]
    return case["status"] not in allowed or any(not check["ok"] for check in case["checks"])


def input_summary(case):
    parts = []
    query = dict(parse_qsl(urlsplit(case["path"]).query, keep_blank_values=True))
    if query:
        parts.append("Query: `" + compact(query) + "`")
    if case.get("request") is not None:
        parts.append("JSON: `" + compact(case["request"]) + "`")
    if case["name"] == "Checkout com card numérico":
        parts.append("`card` era numérico; valor mascarado na evidência")
    return "<br>".join(parts) or "Sem payload nem query; parâmetros, quando presentes, constam no caminho."


def response_summary(case):
    body = case["body"]
    if case["status"] is None:
        return str(body)
    if isinstance(body, str):
        if re.match(r"\s*(?:<!doctype\s+html|<html\b)", body, re.I):
            return f"Resposta HTML (HTTP {case['status']}); sem objeto JSON."
        return "Texto: `" + compact(body) + "`"
    if isinstance(body, list):
        if not body:
            return "Lista vazia (`[]`)."
        if all(isinstance(item, dict) for item in body):
            keys = sorted({key for item in body for key in item})
            # Include actual aggregate values while omitting entire seed lists.
            aggregates = [f"revenue={sum(item['revenue'] for item in body)}"] if all(isinstance(item.get('revenue'), (int, float)) for item in body) else []
            return f"Lista com {len(body)} item(ns); campos: `" + ", ".join(keys) + "`." + (" " + "; ".join(aggregates) if aggregates else "")
        return "`" + compact(body) + "`"
    if not isinstance(body, dict):
        return "`" + compact(body) + "`"
    parts = []
    for key, value in body.items():
        if isinstance(value, list):
            keys = sorted({field for item in value if isinstance(item, dict) for field in item})
            part = f"`{key}`: lista com {len(value)} item(ns)"
            if keys:
                part += "; campos: `" + ", ".join(keys) + "`"
        elif isinstance(value, dict):
            scalar = {k: v for k, v in value.items() if not isinstance(v, (dict, list))}
            part = f"`{key}`: `" + compact(scalar) + "`"
            nested = [k for k, v in value.items() if isinstance(v, (dict, list))]
            if nested:
                part += "; campos adicionais: `" + ", ".join(nested) + "`"
        else:
            part = f"`{key}={compact(value)}`"
        parts.append(part)
    return "; ".join(parts) or "Objeto vazio (`{}`)."


def database_summary(case):
    before, after = case.get("db_before", {}), case.get("db_after", {})
    if before.get("indisponivel") or after.get("indisponivel"):
        return "Observação do banco indisponível após a falha do processo; não foi possível confirmar o estado posterior."
    changes = [f"`{table}`: {before.get(table, '—')} → {after.get(table, '—')}"
               for table in sorted(set(before) | set(after)) if before.get(table) != after.get(table)]
    parts = ["Contagens: " + "; ".join(changes) + "." if changes else "Contagens das tabelas sem variação."]
    for check in case.get("checks", []):
        if re.search(r"persist|SQLite|estoque|órf|removid|usuário não duplicado", check["name"], re.I):
            # Label observations explicitly: a failed check name is a goal, not a fact.
            parts.append(f"Check de persistência «{check['name']}»: observado `" + compact(check["actual"]) + "`" + (" (divergente do esperado)" if not check["ok"] else "") + ".")
    if case["name"] == "Cliente promove usuário a admin sem autorização":
        parts.append("A comparação com o SELECT confirmou a promoção indevida para admin.")
    if case["name"] in {"Inativar usuário sintético", "Reativar usuário sintético"}:
        active = case.get("body", {}).get("active") if isinstance(case.get("body"), dict) else None
        parts.append(f"A resposta informou active={compact(active)}; esse campo não teve SELECT direto registrado neste cenário.")
    for note in case.get("notes", []):
        if re.search(r"varia|receita|criação ocorre|persist", note, re.I):
            parts.append(note)
    return " ".join(parts)


def decision_summary(case):
    if deviates(case):
        if case["name"] in CORRECTIONS:
            return CORRECTIONS[case["name"]]
        failed = [check["name"] for check in case.get("checks", []) if not check["ok"]]
        return "Corrigir: " + (case.get("expectation") or "; ".join(failed) or f"retornar HTTP {case['expected_status']}")
    if case["name"] == "Checkout com pagamento recusado":
        return "Preservar HTTP 400 sem matrícula/pagamento; revisar a criação do usuário antes da recusa, observada no legado."
    if case.get("expectation"):
        return "Preservar: " + case["expectation"]
    return f"Preservar HTTP {case['status']} e o comportamento verificado de «{case['name']}»."


def table_lines(cases):
    lines = ["## Baseline por método e rota", "",
             "Uma linha por cenário executado, identificado pelo ID e pelo nome na primeira coluna. Valores sensíveis permanecem mascarados. Contagens sem variação não comprovam ausência de updates; os checks de persistência informam os valores observados. A indicação de preservar se limita às verificações deste cenário.", "",
             HEADER, "|---|---|---|---|---|---|"]
    for case in cases:
        route = urlsplit(case["path"]).path
        values = [f"`{case['method']} {route}`<br>**{case['id']}** — {case['name']}",
                  input_summary(case), case["status"] if case["status"] is not None else "Sem resposta HTTP",
                  response_summary(case), database_summary(case), decision_summary(case)]
        lines.append("| " + " | ".join(cell(value) for value in values) + " |")
    return lines + [""]


def refresh_report(report_path, evidence):
    path = Path(report_path)
    original = path.read_text()
    table = "\n".join(table_lines(evidence["cases"])) + "\n"
    updated, count = re.subn(
        r"^## (?:Matriz de cenários|Baseline por método e rota)\n.*?(?=^## Desvios observados\n)",
        lambda _: table, original, count=1, flags=re.M | re.S,
    )
    if count != 1:
        raise ValueError(f"Seção da baseline não encontrada: {path}")
    path.write_text(updated)
