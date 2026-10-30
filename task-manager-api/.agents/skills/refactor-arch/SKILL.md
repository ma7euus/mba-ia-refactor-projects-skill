---
name: refactor-arch
description: >-
  Analisa e audita projetos de backend e conduz sua refatoração para MVC após
  confirmação humana. Use para auditorias arquiteturais, identificação de code
  smells e refatoração de APIs legadas. Não usar para perguntas conceituais
  sobre MVC ou alterações isoladas de nomenclatura.
---

# Refactor Arch

**Status:** estrutura inicial. O catálogo, o playbook e as instruções detalhadas
das fases ainda precisam ser preenchidos antes do uso da skill.

## Fase 1 — Análise

Referência: [Análise de projeto](references/project-analysis.md).

Preparar as instruções para detectar stack, banco, domínio e arquitetura atual,
mapear rotas e dependências e apresentar o resumo do projeto.

## Fase 2 — Auditoria

Referências:

- [Catálogo de anti-patterns](references/anti-patterns.md).
- [Template de relatório](references/audit-report-template.md).

Preparar as instruções para identificar problemas com arquivo e linhas exatos,
classificar por severidade e exibir o relatório com a proposta de refatoração.

**Pausa obrigatória:** aguardar confirmação humana antes de modificar qualquer
arquivo. Salvar o relatório e refatorar somente após essa confirmação.

## Fase 3 — Refatoração e validação

Referências:

- [Guidelines MVC](references/mvc-guidelines.md).
- [Playbook de refatoração](references/refactoring-playbook.md).

Preparar as instruções para salvar a auditoria aprovada, aplicar as
transformações MVC, validar boot e endpoints e registrar os resultados.
