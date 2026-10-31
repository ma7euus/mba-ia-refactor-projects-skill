# MVC Architecture Guidelines

<!-- WHAT: the target architecture contract for the Phase 2 proposal and Phase 3.
HOW: define responsibilities before choosing framework-specific folders.
WHY: lesson 11's orchestration examples are useful, but the assignment's target
is MVC; copying a different architecture or directory tree would miss the goal. -->

## Responsibilities and dependency direction

| Part | Owns | Must not own |
|---|---|---|
| Models / data access | Entities, domain invariants and persistence operations | HTTP request/response objects, routing or rendering |
| Views / routes / serializers | Endpoint registration, HTTP adaptation and explicit public response representation | SQL, multi-step business rules or transaction policy |
| Controllers | Application flow: coordinate validated input, domain operations and outcomes | Database connection setup, raw SQL, secret configuration or an entire domain's business logic |
| Optional services | Reusable workflows involving several models or integrations | Framework-global HTTP state or another monolithic manager |
| Composition root | Construct dependencies, initialize the application, register routes and error handlers | Domain decisions or endpoint-specific queries |

<!-- WHAT: MVC for an API that may have no HTML pages.
HOW: treat JSON representation as presentation, with routes adapting HTTP to a
controller and serializers selecting public fields.
WHY: adding an unused templates folder does not provide separation, and moving
everything into controllers merely relocates the original God Module. -->

Use this dependency flow: routes/presentation → controllers → domain/models,
optionally through focused application services. Construct/inject data access
and integration dependencies at the composition root. Models and services should
not import route modules or read framework-global requests. Serialize explicit
public fields rather than dumping every database column.

Choose the simplest organization that makes those boundaries observable.
Keep existing layers that already satisfy them. Avoid an empty service for every
controller, additional frameworks, or a dependency-injection container unless a
concrete requirement justifies it.

## Framework adaptations

<!-- WHAT: illustrative mappings rather than a mandatory scaffold.
HOW: retain the project's startup contract and adopt its import/module style.
WHY: stack neutrality comes from equivalent responsibilities, not identical
filenames or switching CommonJS, ESM, ORMs or Python packaging unnecessarily. -->

| Concern | Python / Flask | Node.js / Express |
|---|---|---|
| Construction | Application factory that wires config, data access and blueprints | App factory wiring config, dependencies, routers and middleware |
| Routing | Blueprints or explicit route registrations delegating flow | Routers delegating to controllers |
| Presentation | JSON serializers with an explicit field allowlist | Response mappers with an explicit field allowlist |
| Controllers | Functions or small classes accepting explicit inputs/dependencies | Functions/classes receiving explicit dependencies |
| Persistence | Existing sqlite3/ORM mechanism with defined connection/session lifetime | Existing database client/ORM with a defined lifetime |
| Errors | Registered handlers translating known application errors into responses | Error middleware registered after routes; propagate async failures correctly for the installed Express version |
| Startup | Existing entry point delegates to the factory | Existing package start command delegates to app/server composition |

For example, a Flask application can expose `app.py` as its stable launcher and
keep config, models, controllers, routes, serializers and errors in an importable
package. An Express application can keep `src/` with the same responsibilities
and a small server entry point. These are examples, not filenames to impose on
every project. Use additional View components only where presentation requires
them; API routes plus serializers satisfy the presentation responsibilities.

## Configuration, connections and data preservation

<!-- WHAT: separate configuration and resource lifetime from business behavior.
HOW: read external configuration once, inject dependencies and close/rollback
resources according to the framework's lifecycle.
WHY: renaming a global database variable or moving a literal secret to another
source file does not fix coupling or credential exposure. -->

- Extract secrets and environment-dependent settings to a configuration boundary.
  Require appropriate external values; do not introduce a shared fallback secret.
  Document required variable names without recording real credentials.
- Preserve database location and data unless the approved plan explicitly defines
  a migration. Turning a persistent file into an in-memory database, changing a
  relative path, or recreating a schema can silently lose the existing data.
- Give connections/sessions an explicit owner and lifetime. For Flask, a
  context-bound connection or existing ORM lifecycle can provide isolation and
  cleanup; `g` is a context-local facility, not a process-wide mutable cache.
- Group writes that must succeed together in a transaction; validate quantities,
  stock and foreign references before committing. Roll back partial operations.
- Migrate password storage without silently locking out existing users. Document
  and verify the chosen transition/reset strategy with synthetic users first.
- Keep seed/reset actions separate from ordinary imports and startup. Validate
  destructive paths only against isolated disposable data.

## HTTP contracts and security corrections

<!-- WHAT: compatibility means preserving valid behavior, not known defects.
HOW: list intentional changes beside their reason and matching verification.
WHY: existing routes may need authorization, serializers must omit passwords,
and malformed inputs should not retain an accidental HTTP 500 contract. -->

Inventory method/path, path/query/body fields, success/error responses,
authorization and database effects before restructuring. Preserve valid contracts
and documented business rules. Identify any deliberate changes in the Phase 2
plan: removing secret fields, enforcing authorization, rejecting invalid input,
fixing nonexistent-ID handling or restricting dangerous administrative actions.

Keep original method/path registrations implemented with appropriately authorized,
bounded behavior. For dangerous database controls, propose a restricted operation
with an explicit safe contract instead of silently deleting the endpoint. A 404
from a removed route is not evidence that the original operation still works.
If safe retention is impossible, expose the conflict in the proposal and leave
the endpoint-continuity criterion unresolved rather than marking it passed.

Do not invent a login/token protocol merely to add an authentication decorator.
Use the existing verified identity mechanism or propose a concrete minimal
alternative with provisioning and authorized/unauthorized test cases. Never
trust a client-supplied user ID, role or header as proof of authority. Do not leave
a protected operation unreachable to legitimate test users without documenting
how authorization is established.

Classify errors at a shared boundary. Translate expected validation, not-found
and authorization failures into the agreed 4xx contract. Return a generic 5xx
response for unexpected failures and retain sanitized diagnostics. Avoid catching
all failures and returning HTTP 200 or exposing database statements and secrets.
In Express, preserve four-argument error middleware and check the installed
version's async propagation behavior; do not assume Express 5 behavior in 4.x.

## Validation contract

<!-- WHAT: a measurable completion rule.
HOW: boot the edited code and exercise the route inventory with isolated state;
separate counts, field values and indirect API evidence.
WHY: lesson 14 evaluates quality independently of triggering, and lesson 12
requires checking actual command outcomes rather than accepting a summary. -->

1. Record the commands and environment used to start the current edited code.
   Confirm readiness and inspect startup errors; do not infer a boot from imports.
2. Run every inventoried method/route with a valid fixture and relevant failure
   cases. Check original status/payload contracts or the approved corrections.
3. Verify effects: created/deleted rows, changed fields, totals, stock, foreign
   references and rollback after a refused operation. Equal row counts alone do
   not prove an update or an absence of mutation.
4. Verify security corrections without disclosing secret values: explicit public
   serializers, appropriate password verification, real authorization checks,
   safe configuration and errors, and denied invalid requests.
5. Use synthetic credentials and disposable databases. Keep simulated payments
   and notifications simulated; record any integration that could not be tested.
6. Inspect the test runner's source target. An existing legacy-baseline runner
   pinned to an old Git commit does not test the current refactored application.
   Reuse its cases against the current code with the same intentional fixtures.
7. Record observed results and unresolved failures separately from the original
   audit. Report a command failure or missing prerequisite instead of claiming a
   pass. Reinspect responsibility boundaries and the corrected catalog entries.

Conclude only after the application boots, every inventoried operation is
verified, and each approved finding has correction evidence. If a runtime check
cannot be performed, report that limitation and leave validation incomplete.
