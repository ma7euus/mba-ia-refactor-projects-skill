#!/usr/bin/env python3
"""Registra a baseline do commit legado, sem modificar código ou bancos locais."""

import argparse
import importlib
import json
import sys

from common import Baseline, ROOT
from reporting import refresh_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=int, choices=(1, 2, 3))
    parser.add_argument("--render-only", action="store_true",
                        help="Atualiza as tabelas usando os JSONs existentes, sem executar aplicações")
    args = parser.parse_args()
    projects = {1: "code-smells-project", 2: "ecommerce-api-legacy", 3: "task-manager-api"}
    failed = False
    for number in ([args.project] if args.project else projects):
        if args.render_only:
            reports = ROOT / "reports"
            evidence = json.loads((reports / "evidence" / f"baseline-project-{number}.json").read_text())
            report = reports / f"baseline-project-{number}.md"
            refresh_report(report, evidence)
            print(f"Tabela atualizada: {report.relative_to(ROOT)}", flush=True)
            continue
        baseline = Baseline(projects[number], number)
        error = None
        try:
            importlib.import_module(f"project_{number}").run(baseline)
        except Exception as exc:
            # Avoid writing exception values that could include response secrets.
            error = f"{type(exc).__name__}: execução interrompida; investigar executor e log sanitizado"
            failed = True
        finally:
            summary = baseline.finish(error)
            print(json.dumps(summary, ensure_ascii=False), flush=True)
            failed |= bool(summary["uncovered"] or not summary["source_unchanged"])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
