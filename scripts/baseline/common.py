"""Execução HTTP de cópias temporárias do legado, com evidências sanitizadas."""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import queue
import re
import socket
import sqlite3
import subprocess
import tarfile
import tempfile
import threading
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler

from reporting import table_lines


COMMIT = "6d1ce6248c3e956801010a89d8bdaab48029bf30"
ROOT = Path(__file__).absolute().parents[2]
SENSITIVE = re.compile(
    r"password|senha|secret|token|authorization|dbpass|gatewaykey|^pass$|^pwd$|^card$|^cc$",
    re.I,
)


def scrub(value):
    if isinstance(value, dict):
        return {str(k): "[MASCARADO]" if SENSITIVE.search(str(k)) else scrub(v)
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [scrub(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


def exposes_secret(value):
    if isinstance(value, dict):
        return any(
            (str(key).lower() in {"senha", "password", "pass", "pwd", "secret_key"})
            or exposes_secret(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(exposes_secret(item) for item in value)
    return False


class Baseline:
    def __init__(self, project, number):
        self.project, self.number = project, number
        self.temp = tempfile.TemporaryDirectory(prefix=f"refactor-baseline-{number}-")
        self.workspace = Path(self.temp.name) / project
        archive = subprocess.run(
            ["git", "archive", COMMIT, project], cwd=ROOT,
            check=True, capture_output=True,
        ).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            source.extractall(self.temp.name, filter="data")
        self.db_path = self.workspace / ("instance/tasks.db" if number == 3 else "loja.db")
        self.python = ROOT / project / ".venv/bin/python"
        self.results = []
        self.routes = []
        self.findings = []
        self.limitations = []
        self.process = None
        self.port = None
        self.raw_logs = []
        self.reader_threads = []
        self.responses = queue.Queue()
        self.query_id = 0
        self.boots = []
        self.versions = {}
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.opener = build_opener(ProxyHandler({}))
        self.before_hashes = self.source_hashes()

    def source_hashes(self):
        return {str(p.relative_to(self.workspace)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.workspace.rglob("*")
                if p.is_file() and p.suffix in {".py", ".js", ".json", ".txt"}
                and "node_modules" not in p.parts and "__pycache__" not in p.parts
                and not p.name.startswith("baseline-")}

    def inventory(self, routes):
        self.routes = [(method.upper(), path) for method, path in routes]

    def add_finding(self, text):
        if text not in self.findings:
            self.findings.append(text)

    def add_limitation(self, text):
        if text not in self.limitations:
            self.limitations.append(text)

    def _collect(self, pipe, stream):
        for line in iter(pipe.readline, ""):
            if line.startswith("BASELINE_RESULT:"):
                try:
                    self.responses.put(json.loads(line.split(":", 1)[1]))
                except json.JSONDecodeError:
                    self.raw_logs.append(f"{stream}: resposta inválida do observador SQLite\n")
            else:
                self.raw_logs.append(f"{stream}: {line}")
        pipe.close()

    def _launch(self, command, entry):
        self.process = subprocess.Popen(
            command, cwd=self.workspace, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"},
        )
        for stream in ("stdout", "stderr"):
            reader = threading.Thread(target=self._collect,
                                      args=(getattr(self.process, stream), stream), daemon=True)
            reader.start()
            self.reader_threads.append(reader)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"Boot falhou: {self.project}; código {self.process.returncode}")
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.2):
                    self.boots.append({"entry_point": entry, "host": "127.0.0.1",
                                       "port": self.port, "ready": True})
                    return
            except OSError:
                time.sleep(0.05)
        raise RuntimeError(f"Timeout no boot: {self.project}")

    def _free_port(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]

    def start_flask(self, seed=False):
        if not self.python.exists():
            raise RuntimeError(f"Ambiente ausente: {self.python}")
        package_names = ["flask", "flask-cors"]
        if seed:
            package_names += ["flask-sqlalchemy", "sqlalchemy"]
        versions = subprocess.run(
            [str(self.python), "-c",
             "import json,sys; from importlib.metadata import version; "
             f"print(json.dumps({{'python':sys.version.split()[0], **{{p:version(p) for p in {package_names!r}}}}}))"],
            check=True, capture_output=True, text=True,
        )
        self.versions = json.loads(versions.stdout)
        if seed:
            seeded = subprocess.run([str(self.python), "seed.py"], cwd=self.workspace,
                                    capture_output=True, text=True, timeout=30,
                                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            self.raw_logs += ["seed stdout: " + seeded.stdout, "seed stderr: " + seeded.stderr]
            if seeded.returncode:
                raise RuntimeError(f"Seed falhou; código {seeded.returncode}")
        self._free_port()
        wrapper = f"""
import json, runpy
from pathlib import Path
from flask import Flask
original_run = Flask.run
def isolated_run(self, *args, **kwargs):
    routes = [{{'method': method, 'path': rule.rule}} for rule in self.url_map.iter_rules()
              if rule.endpoint != 'static' for method in sorted(rule.methods - {{'HEAD', 'OPTIONS'}})]
    Path('baseline-routes.json').write_text(json.dumps(routes))
    kwargs.update(host='127.0.0.1', port={self.port}, debug=False, use_reloader=False)
    return original_run(self, *args, **kwargs)
Flask.run = isolated_run
runpy.run_path('app.py', run_name='__main__')
"""
        self._launch([str(self.python), "-c", wrapper], "python app.py via runpy; porta isolada; debug/reloader desativados")

    def start_node(self):
        modules = ROOT / self.project / "node_modules"
        if not modules.exists():
            raise RuntimeError(f"Dependências ausentes: {modules}")
        link = self.workspace / "node_modules"
        if not link.exists():
            link.symlink_to(modules, target_is_directory=True)
        self.versions = {"node": subprocess.run(["node", "--version"], check=True,
                                                 capture_output=True, text=True).stdout.strip()}
        for name in ("express", "sqlite3"):
            self.versions[name] = json.loads((modules / name / "package.json").read_text())["version"]
        self._free_port()
        wrapper = f"""
const fs = require('fs');
const http = require('http');
const sqlite = require('sqlite3');
const OriginalDatabase = sqlite.Database;
let observedDb;
sqlite.Database = function(...args) {{ observedDb = new OriginalDatabase(...args); return observedDb; }};
sqlite.Database.prototype = OriginalDatabase.prototype;
const originalListen = http.Server.prototype.listen;
http.Server.prototype.listen = function(...args) {{
  const app = this.listeners('request')[0];
  const routes = (app._router?.stack || []).filter(x => x.route).flatMap(x =>
    Object.keys(x.route.methods).filter(m => x.route.methods[m]).map(m => ({{method:m.toUpperCase(), path:x.route.path}})));
  fs.writeFileSync('baseline-routes.json', JSON.stringify(routes));
  return originalListen.call(this, {{port:{self.port}, host:'127.0.0.1'}}, ...args.filter(x => typeof x === 'function'));
}};
require('./src/utils').config.port = {self.port};
require('./src/app');
require('readline').createInterface({{input:process.stdin}}).on('line', line => {{
  const command = JSON.parse(line);
  if (!/^\\s*SELECT\\b/i.test(command.sql)) {{
    console.log('BASELINE_RESULT:' + JSON.stringify({{id:command.id, error:'Somente SELECT permitido'}})); return;
  }}
  observedDb.all(command.sql, command.params, (error, rows) => {{
    console.log('BASELINE_RESULT:' + JSON.stringify({{id:command.id, error:error?.message, rows}}));
  }});
}});
"""
        self._launch(["node", "-e", wrapper], "node src/app.js via require; porta isolada; observador SQLite somente SELECT")

    def restart_node(self):
        self.stop()
        self.start_node()

    def node_query(self, sql, params=()):
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("Processo Node indisponível")
        if not re.match(r"\s*SELECT\b", sql, re.I):
            raise ValueError("Observador permite apenas SELECT")
        self.query_id += 1
        self.process.stdin.write(json.dumps({"id": self.query_id, "sql": sql, "params": list(params)}) + "\n")
        self.process.stdin.flush()
        response = self.responses.get(timeout=5)
        if response.get("id") != self.query_id or response.get("error"):
            raise RuntimeError("Falha no observador SQLite")
        return response["rows"]

    def query(self, sql, params=()):
        with sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute(sql, params).fetchall()]

    def snapshot(self):
        try:
            query = self.node_query if self.number == 2 else self.query
            names = query("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
            return {row["name"]: query('SELECT COUNT(*) AS total FROM "' + row["name"].replace('"', '""') + '"')[0]["total"]
                    for row in names}
        except (RuntimeError, OSError, sqlite3.Error, queue.Empty):
            return {"indisponivel": True}

    def case(self, name, method, path, payload=None, expected=200, expectation="", route=None):
        before = self.snapshot()
        request = Request(f"http://127.0.0.1:{self.port}{path}", method=method,
                          data=json.dumps(payload).encode() if payload is not None else None,
                          headers={"Content-Type": "application/json"} if payload is not None else {})
        result = {"id": f"P{self.number}-{len(self.results)+1:02d}", "name": name,
                  "method": method, "path": path, "route": route or path.split("?", 1)[0],
                  "request": payload, "expected_status": expected, "expectation": expectation,
                  "checks": [], "notes": [], "db_before": before}
        started = time.monotonic()
        try:
            try:
                response = self.opener.open(request, timeout=8)
            except HTTPError as error:
                response = error
            with response:
                result["status"] = response.code
                result["content_type"] = response.headers.get("Content-Type", "")
                body = response.read().decode("utf-8", errors="replace")
            try:
                result["body"] = json.loads(body)
            except json.JSONDecodeError:
                result["body"] = body
        except (URLError, OSError, TimeoutError) as error:
            result.update(status=None, body=f"Falha de transporte: {type(error).__name__}")
        except Exception as error:
            # Includes a closed HTTP connection after a server-side crash.
            result.update(status=None, body=f"Falha de transporte: {type(error).__name__}")
        result["duration_ms"] = round((time.monotonic()-started)*1000, 2)
        result["db_after"] = self.snapshot()
        self.check(result, "Resposta omite campos de senha/hash/segredo", exposes_secret(result["body"]), False)
        self.results.append(result)
        return result

    def check(self, result, name, actual, expected):
        result["checks"].append({"name": name, "actual": actual,
                                 "expected": expected, "ok": actual == expected})

    def note(self, result, text):
        result["notes"].append(text)

    def has_log(self, pattern):
        return bool(re.search(pattern, "".join(self.raw_logs), re.I))

    def stop(self):
        if self.process:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            for reader in self.reader_threads:
                reader.join(timeout=2)
            self.process = None
            self.reader_threads = []

    def _clean_log(self):
        lines = []
        for line in "".join(self.raw_logs).splitlines():
            if re.search(r"password|senha|secret|token|cart[aã]o|card\b|chave|gatewaykey|debugger pin|\bpwd\b|\bpass\b", line, re.I):
                lines.append("[linha com dados potencialmente sensíveis omitida]")
            else:
                lines.append(line.replace(self.temp.name, "<workspace-temporario>"))
        return "\n".join(lines) + "\n"

    @staticmethod
    def deviates(result):
        expected = result["expected_status"]
        allowed = expected if isinstance(expected, (list, tuple)) else [expected]
        return result["status"] not in allowed or any(not c["ok"] for c in result["checks"])

    def finish(self, error=None):
        exit_before_cleanup = self.process.poll() if self.process else None
        self.stop()
        actual_inventory = json.loads((self.workspace / "baseline-routes.json").read_text()) if (self.workspace / "baseline-routes.json").exists() else []
        actual_routes = {(r["method"], r["path"]) for r in actual_inventory}
        exercised = {(r["method"], r["route"]) for r in self.results}
        inventory = actual_routes or set(self.routes)
        uncovered = sorted(inventory - exercised)
        source_unchanged = self.source_hashes() == self.before_hashes
        deviations = [r for r in self.results if self.deviates(r)]
        document = {
            "project": self.project, "commit_base": COMMIT, "started_at_utc": self.started_at,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(), "versions": self.versions,
            "isolation": "git archive em /tmp; banco descartável; dependências locais reutilizadas",
            "runtime_adjustments": "HTTP real em loopback e porta efêmera; Flask sem debug/reloader; Node com observador SQLite somente SELECT",
            "boots": self.boots, "source_unchanged": source_unchanged,
            "process_exit_before_cleanup": exit_before_cleanup,
            "source_sha256": self.before_hashes,
            "coverage": {"inventory": sorted(inventory), "covered": sorted(inventory & exercised),
                         "uncovered": uncovered, "declared_inventory_matches_runtime": set(self.routes) == actual_routes},
            "case_count": len(self.results), "deviation_count": len(deviations),
            "findings": self.findings, "limitations": self.limitations,
            "execution_error": error, "cases": self.results,
        }
        reports = ROOT / "reports"
        evidence = reports / "evidence"
        evidence.mkdir(parents=True, exist_ok=True)
        stem = f"baseline-project-{self.number}"
        (evidence / f"{stem}.json").write_text(json.dumps(scrub(document), ensure_ascii=False, indent=2) + "\n")
        (evidence / f"{stem}.log").write_text(self._clean_log())
        lines = [f"# Baseline — {self.project}", "",
                 f"- **Commit-base:** `{COMMIT}`.",
                 f"- **Execução (UTC):** {self.started_at}.",
                 f"- **Ambiente observado:** `{json.dumps(self.versions, ensure_ascii=False)}`.",
                 "- **Isolamento:** cópia do commit-base em diretório temporário; banco descartável; bancos locais preservados.",
                 "- **HTTP:** servidor real em loopback e porta efêmera. Flask executa o entry point por `runpy`, com debug e reloader desativados. Node carrega o entry point por `require`, com observador SQLite que aceita somente SELECT.",
                 f"- **Código da aplicação preservado na execução:** {'sim' if source_unchanged else 'NÃO'}.",
                 f"- **Cobertura de operações:** {len(inventory & exercised)}/{len(inventory)} combinações método/rota.",
                 f"- **Cenários:** {len(self.results)}; **cenários com desvios:** {len(deviations)}.", "",
                 "As expectativas representam o comportamento correto desejado. Um desvio documenta uma falha observada do legado; não é resultado a perpetuar na refatoração. Esta baseline não é o relatório da Fase 2 da skill.", "",
                 f"Requisições, respostas completas sanitizadas, verificações e contagens de tabelas: [evidência JSON](evidence/{stem}.json). Boot, avisos e erros: [log sanitizado](evidence/{stem}.log).", "",
                 "## Operações inventariadas", "", "| Método | Rota | Exercitada |", "|---|---|---|"]
        for method, path in sorted(inventory):
            lines.append(f"| {method} | `{path}` | {'Sim' if (method, path) in exercised else 'Não'} |")
        lines += [""] + table_lines(scrub(self.results))
        lines += ["", "## Desvios observados", ""]
        for result in deviations:
            failed = [c["name"] for c in result["checks"] if not c["ok"]]
            detail = result["expectation"].rstrip(". ")
            if failed:
                detail += ("; " if detail else "") + "verificações reprovadas: " + "; ".join(failed)
            status = f"HTTP {result['status']}" if result['status'] is not None else "sem resposta HTTP"
            lines.append(f"- **{result['id']} — {result['name']}:** {status}; {detail or 'divergência de status ou contrato' }.")
        if not deviations:
            lines.append("Nenhum desvio nos cenários executados.")
        if self.findings:
            lines += ["", "## Observações de comportamento", ""] + [f"- {s}" for s in self.findings]
        lines += ["", "## Reprodução e limites", "", "```bash",
                  f"python3 scripts/baseline/run.py --project {self.number}", "```", "",
                  "Usa as dependências já instaladas em `.venv` de cada Flask e `node_modules` do LMS. A fonte é sempre o commit-base, não o código corrente. A configuração de rede/debug e a instrumentação pertencem ao executor, sem editar os fontes legados.", ""]
        lines += [f"- {s}" for s in self.limitations]
        lines += ["- A cobertura mede operações exercitadas, não cobertura de linhas, carga ou todos os caminhos possíveis.",
                  "- Dados sensíveis são mascarados nas evidências. IDs, timestamps, portas e datas relativas do seed podem variar entre execuções."]
        if error:
            lines += [f"- **Erro do executor:** {error}"]
        (reports / f"{stem}.md").write_text("\n".join(lines) + "\n")
        summary = {"project": self.project, "cases": len(self.results),
                   "covered": len(inventory & exercised), "routes": len(inventory),
                   "deviations": len(deviations), "uncovered": uncovered,
                   "source_unchanged": source_unchanged, "error": error}
        self.temp.cleanup()
        return summary
