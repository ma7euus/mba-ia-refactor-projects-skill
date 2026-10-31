# Project Analysis

<!-- WHAT: the Phase 1 discovery reference, loaded when analysis begins.
HOW: combine manifests, imports, entry points and call relationships instead of
guessing from a folder name. WHY: lessons 2/3/8 separate targeted knowledge from
the entry point; the same instructions must work across backend technologies. -->

## 1. Establish the target and source snapshot

Identify the requested application directory, its containing repository, and
any report destination supplied by the caller. Treat neighboring applications
as outside the source scope unless explicitly included.

Use available read-only tools to inspect the current directory, repository root,
commit, and relevant worktree status. Useful commands include `git rev-parse
--show-toplevel`, `git rev-parse HEAD`, `git status --short`, `rg --files`, and
`nl -ba` for source line evidence. Adapt commands to the environment; do not
redirect their output into files during discovery.

<!-- WHAT: a snapshot that can still explain line numbers after files move.
HOW: record a supplied baseline commit only after comparing it to target source;
include dirty/untracked source and per-file hashes when needed.
WHY: a clean application can live in a dirty monorepo, and HEAD can differ from
the historical commit. Neither circumstance justifies inventing provenance. -->

- If the caller supplies a commit, check whether the relevant application source
  matches it. Record mismatches instead of labeling modified files as that commit.
- Distinguish application source changes from unrelated documentation and skill
  changes. Report relevant dirty and untracked source explicitly.
- For files not represented by the commit, retain relative path, current SHA-256,
  and the statement that findings refer to those working-tree bytes.
- Without Git, identify the snapshot by source hashes and report the commit as
  unavailable. Do not initialize a repository to manufacture a commit reference.
- Keep findings anchored to this pre-refactoring snapshot. If source changes
  during discovery, refresh affected evidence before presenting the audit.

## 2. Build a bounded inventory

<!-- WHAT: meaningful counts rather than the size of the dependency tree.
HOW: count first-party source, tests and supporting files separately and state
the rules. WHY: lesson 8 demonstrates deterministic collection plus exclusions;
a scanner's file count must not masquerade as complete architectural analysis. -->

Start with source extensions, tracked files and applicable ignore rules. Include
relevant untracked first-party source, but exclude `.git/`, virtual environments,
`node_modules/`, build outputs, generated code, caches, database files, reports,
and this skill bundle from application source counts. Inspect relevant manifests
and dependency metadata separately without treating them as authored source.

State whether source counts include empty modules, tests, comments and blank
lines. For LOC, prefer total physical lines with that definition disclosed.
List unreadable or excluded application areas as coverage limits. Do not claim
that listing a file proves every call path was analyzed.

## 3. Detect the stack and persistence

| Evidence | Python / Flask heuristics | Node.js / Express heuristics |
|---|---|---|
| Language | `.py` sources and Python manifests | `.js`/`.mjs`/`.cjs`/`.ts` plus `package.json` |
| Framework | Flask imports, `Flask(...)`, blueprints and decorators | Express import/require, application factory, routers and middleware |
| Dependencies | `requirements*.txt`, `pyproject.toml`, lockfiles | `package.json`, package manager lockfile and installed package metadata |
| Persistence | `sqlite3.connect`, SQL statements, SQLAlchemy URI/models | Database client imports, connection construction, SQL calls and ORM models |
| Startup | documented script, `__main__`, factory or WSGI entry point | package scripts, imported app and `listen`/server entry point |

For another stack, use the same evidence categories with its actual manifests
and framework documentation. State uncertainty when the signals conflict.

<!-- WHAT: declared, resolved and observed versions are different facts.
HOW: read manifests/lockfiles and installed metadata where available.
WHY: a semver range is not an installed version; deprecated-API decisions depend
on this distinction. Do not install or import the application to fill a gap. -->

Record the runtime version, dependency constraints, locked versions, and existing
installed versions separately. Mark missing information as unknown. Use official
documentation for version-sensitive decisions, identifying the version examined.

Trace the database configuration to its actual storage model: memory, file or
external service. Note path resolution, connection/session ownership, schema
creation, foreign keys, transactions, migrations and seeds. Inspect initialization
statically: importing an app can create tables, and running a seed can erase data.
Do not perform those operations in Phases 1 or 2.

## 4. Infer the domain and architectural responsibilities

Determine the domain from entities, route behavior, validations and business
rules. A directory named after e-commerce might implement a learning platform;
names alone are not proof.

Map modules and calls into HTTP routing/presentation, application orchestration,
domain rules, persistence, configuration and external integrations. Record which
module owns each responsibility and where boundaries are crossed. Existing
`models`, `routes`, or `services` folders do not demonstrate correct layering.
Likewise, a long file is not automatically a God Module.

Distinguish actual external calls from simulations, console notifications or
unused services. Do not introduce real payments, email or other side effects to
validate a legacy simulation.

## 5. Inventory operations and existing behavior

<!-- WHAT: the compatibility contract used by auditing and validation.
HOW: reconstruct method/path combinations, inputs and effects from registrations
and existing evidence. WHY: a successful health check alone cannot establish
that CRUD, business workflows or error responses still work (lesson 14). -->

Resolve application and router prefixes, method decorators/registrations,
path parameters, query strings, payloads and middleware order. For dynamic
registrations that cannot be resolved statically, report the limit; do not import
the app or start it before approval. Separate framework-generated HEAD/OPTIONS
and static-file routes from explicitly authored API operations.

For each operation, identify successful and invalid flows, response fields,
status codes, authorization, data mutations and external effects. Use the same
six columns as existing baseline evidence:

| Method and route | Input | Observed status | Relevant response fields | Database effect | Behavior to preserve or failure to correct |
|---|---|---|---|---|---|
| Record an actual inventoried operation | Path/query/body | Historical observation or not executed | Source/evidence-backed fields | Counts, field updates, or unverified | Valid contract or identified defect |

Read available baseline reports and tests. Check their target, commit, versions,
timestamp, database setup and sanitization. Label old observations as historical;
do not report a fresh successful boot based on an existing log. Equal table
counts do not prove that field values were unchanged.

Inspect the test harness before relying on it: a script using `git archive` or
checking out a fixed old commit measures that old snapshot. After refactoring,
adapt the same cases to the current edited code instead of passing an old-code
run off as regression evidence. No repository-specific harness is required for
this skill to work.

## 6. Print the Phase 1 summary

Print a concise record with the following fields, grounded in the inventory:

- Target directory and repository root, when available.
- Source snapshot: commit, relevant dirty/untracked files, and hash limitations.
- Language and framework with evidence.
- Runtime and dependency versions: declared, resolved, installed or unknown.
- Domain, database/storage model, initialization and seed behavior.
- Entry point, startup command, current responsibilities and coupling.
- Authored source count/LOC definition and operation inventory count.
- Available manual findings/baseline evidence and any unverified runtime claims.
- Analysis limits that Phase 2 or approved runtime validation must address.

Keep this summary in the conversation; proceed to the audit without creating
files or running the application.
