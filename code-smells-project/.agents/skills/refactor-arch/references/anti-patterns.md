# Anti-pattern Catalog

<!-- WHAT: Detection knowledge for architectural and code-quality findings.
HOW: Read during Phase 2; inspect only the stack-specific signals that apply.
WHY: Lessons 2, 3, 8 and 10 place substantial knowledge in Level 3 references,
keeping the skill entry point short without coupling it to one application. -->

## Evidence and classification rules

<!-- WHAT: An evidence threshold for findings, rather than a keyword checklist.
HOW: Follow inputs, callers and effects; record exact source locations and the
audited revision. WHY: A search hit is a candidate, not proof of a defect. -->

1. Search for candidates, then read the enclosing function and relevant callers. Trace the input, responsibility or dependency that makes the pattern harmful.
2. Record the project-relative source file (relative to the target root from Phase 1), exact start/end lines, a sanitized evidence excerpt, impact and recommendation. Keep the source revision from Phase 1; distinguish committed code from local changes.
3. Use existing baseline evidence when available. During the read-only phases, do not boot applications, install dependencies, run seeds or invoke endpoints to prove a finding.
4. Label each claim as static evidence or previously observed runtime evidence. State uncertainty explicitly; leave unconfirmed candidates out of confirmed-finding totals.
5. Classify by demonstrated impact and reachability. Explain departures from the default severity below. Do not inflate severity or invent findings to meet a quota.
6. Consolidate repeated occurrences of one underlying problem, listing their locations. Cross-reference related mechanisms instead of counting the same exposure repeatedly under several IDs.
7. Preserve legitimate behavior in the recommendation. Identify intentional contract changes, such as removing a password field or requiring authorization, for review before Phase 3.

<!-- WHAT: A shared severity vocabulary. HOW: Select the highest justified impact
for the specific finding. WHY: Consistent rankings make reports comparable across
languages and distinguish urgent defects from readability improvements. -->

| Severity | Use when the evidence demonstrates |
|---|---|
| **CRITICAL** | Exposed sensitive data, exploitable injection, destructive unauthorized access, or a complete collapse of responsibilities that severely compromises correctness. |
| **HIGH** | Strong MVC/SOLID violations, unsafe credential storage, shared mutable state, missing authorization or broken transaction boundaries with substantial impact. |
| **MEDIUM** | Repeated work, inconsistent validation/error handling, confirmed deprecated APIs or other moderate maintenance/performance defects. |
| **LOW** | Local readability, naming, unnecessary code or unexplained constants without a demonstrated higher-impact defect. |

Each entry maps to the same AP ID in the [refactoring playbook](refactoring-playbook.md). Read the corresponding transformation only after the Phase 2 approval gate when implementing the correction.

## AP-01 — SQL injection

<!-- WHAT: An untrusted-data-to-SQL trace. HOW: Distinguish SQL text construction
from parameter binding. WHY: Similar-looking string interpolation is not equally
dangerous in raw SQL and in an ORM expression that creates bound parameters. -->

- **Default severity:** CRITICAL; client-controlled SQL structure can expose or alter data.
- **Detect:** Python f-strings, concatenation or `%` formatting passed to `execute()`; JavaScript template literals or concatenation passed to `db.get()`, `db.all()` or `db.run()` with request-derived values.
- **Confirm/evidence:** Identify the input source and the SQL execution sink, including both locations when separate. A raw SQL string assembled from a request email is a stronger example than an integer already constrained by a route converter.
- **False-positive guard:** Do not flag bound placeholders with a separate parameter collection. ORM expressions such as `Model.name.like(f"%{term}%")` can bind values safely; inspect generated expression semantics rather than treating every f-string as injection.
- **Impact:** Authentication bypass, disclosure, data corruption or malformed SQL for ordinary input containing an apostrophe.
- **Correction:** Apply **AP-01**: parameterize values and allowlist dynamic identifiers. Verify ordinary quoted text and invalid input after approval; do not execute attack payloads during the audit.

## AP-02 — Exposed secrets or sensitive data

<!-- WHAT: Configuration, response and logging exposure. HOW: Trace where a
sensitive value is defined and where it leaves its intended boundary. WHY: Moving
a literal into configuration does not fix an unsafe serializer or log statement. -->

- **Default severity:** CRITICAL for exposed credentials, signing keys, passwords, password hashes or payment details; justify the actual exposure rather than claiming an unused example is a live secret.
- **Detect:** Secrets in source/config defaults; `jsonify()`/`res.json()` returning credential fields; unrestricted model serialization; logs containing passwords, signing keys or complete payment data.
- **Confirm/evidence:** Cite the definition and reachable response/log sink. Record field names and a masked excerpt, never the sensitive value itself. Inspect whether error/debug responses reveal configuration too.
- **False-positive guard:** Public identifiers, non-sensitive configuration and deliberately synthetic test fixtures are not automatically leaked production credentials. A hash used to verify passwords remains sensitive when returned to clients.
- **Impact:** Credential compromise, offline password attacks, token forgery or disclosure through ordinary API usage and logs.
- **Correction:** Apply **AP-02**: externalize secrets, use explicit response allowlists and sanitize logs/errors. Validate absence of sensitive fields as well as correct normal responses.

## AP-03 — God class or God module

<!-- WHAT: Responsibility concentration. HOW: Inspect dependencies and change
reasons instead of applying a line-count threshold. WHY: A large file is a signal,
while mixed routing, persistence and unrelated business rules are the evidence. -->

- **Default severity:** HIGH; use CRITICAL only when the demonstrated collapse of responsibilities severely compromises correctness or safety.
- **Detect:** One class/module owns routing, database lifecycle, several unrelated domains, payment/notification effects, validation and presentation. Constructors that directly build every dependency strengthen the signal.
- **Confirm/evidence:** List the distinct responsibilities and representative exact ranges; show why one domain change affects unrelated behavior or prevents isolated testing.
- **False-positive guard:** A small composition root may legitimately wire many dependencies. File size, a coordinator name or one cohesive domain model alone does not establish a God object.
- **Impact:** High coupling, difficult testing and broad regression risk from small changes.
- **Correction:** Apply **AP-03**: split cohesive responsibilities into MVC components and necessary services, retaining a clear composition root and public contracts.

## AP-04 — Business rules or persistence in routes/controllers

<!-- WHAT: A misplaced responsibility. HOW: Separate transport translation from
domain decisions and data access. WHY: Renaming a route file to controller does
not improve architecture if its original responsibilities remain mixed. -->

- **Default severity:** HIGH for substantial domain workflows or persistence coupled to HTTP handling.
- **Detect:** Flask handlers or Express callbacks calculate pricing, alter inventory, coordinate multi-step persistence or call external services while building responses; controllers contain raw SQL for several domains.
- **Confirm/evidence:** Identify transport-specific operations and independently meaningful domain/data operations in the same flow. Explain which responsibility moves and which MVC boundary should remain.
- **False-positive guard:** Reading a request, selecting an HTTP status and invoking one application operation are normal boundary responsibilities. Keep simple domain invariants on a cohesive model when appropriate.
- **Impact:** Rules become difficult to reuse or test without HTTP; duplicated handlers drift in behavior.
- **Correction:** Apply **AP-04**: keep controllers coordinating the use case, models/repositories owning persistence and serializers/routes handling presentation/transport; introduce services when the workflow warrants them.

## AP-05 — Insecure password storage

<!-- WHAT: Password verification design. HOW: Trace both storage and login paths.
WHY: Changing only the write path can make existing users unable to authenticate. -->

- **Default severity:** HIGH; classify a separate reachable password disclosure under AP-02 when justified.
- **Detect:** Plaintext equality/storage, unsalted MD5/SHA-1, raw fast general-purpose hashes, Base64/truncated encoding presented as a password hash, or a default password silently assigned by the application.
- **Confirm/evidence:** Locate creation/update and verification code; inspect existing schema expectations and sanitized baseline checks without printing stored values.
- **False-positive guard:** Checksums, non-secret identifiers and intentionally synthetic fixture values are not password hashing. Verify a hashing helper's implementation before judging it by its name.
- **Impact:** Recoverable or cheaply guessable credentials and authentication inconsistencies.
- **Correction:** Apply **AP-05**: use a maintained password-hashing API, update verification and plan migration/reset for existing accounts. Preserve valid login behavior without retaining insecure storage.

## AP-06 — Mutable global state or uncontrolled dependency lifetime

<!-- WHAT: Hidden state shared between requests. HOW: Trace writers, ownership
and lifetime. WHY: Globals are not inherently wrong; undocumented mutable state
and unsafe shared connections are the actual architectural concern. -->

- **Default severity:** HIGH when state or connections can leak across requests, race or prevent isolation.
- **Detect:** Mutable module-level caches/counters, process-wide database connections reused without an appropriate lifecycle, handlers importing mutable collections, or services creating their own hidden global dependencies.
- **Confirm/evidence:** Identify mutations and consumers, connection cleanup and intended concurrency model. Distinguish a demonstrated lifecycle defect from a possible concurrency issue requiring later validation.
- **False-positive guard:** Immutable constants, application-scoped configured dependencies and documented synchronized caches can be legitimate.
- **Impact:** Order-dependent tests, stale data, resource leaks, unintended sharing or concurrency failures.
- **Correction:** Apply **AP-06**: define ownership, inject dependencies and scope mutable state/connections to the appropriate request or application lifecycle.

## AP-07 — N+1 queries and repeated data access

<!-- WHAT: Data-access work that grows with each returned item. HOW: Inspect loop
boundaries and ORM loading strategies. WHY: Existing relationships or an identity
map may change the number of actual queries, so avoid invented query counts. -->

- **Default severity:** MEDIUM for repeated queries on a normal list/report path.
- **Detect:** A query inside a loop over parent rows; nested course/user/item lookups; lazy relationships accessed while serializing each record; per-record counts instead of grouped aggregates.
- **Confirm/evidence:** Cite the outer collection and inner database operation. Explain the growth relationship; use measured counts only when existing runtime evidence actually records them.
- **False-positive guard:** Check eager loading, cached values, ORM identity-map behavior and bounded batch size. Several independent aggregate queries are not automatically N+1.
- **Impact:** Latency and database load grow with the response size.
- **Correction:** Apply **AP-07**: join, batch, prefetch or aggregate while preserving missing relationships, result shape and totals.

## AP-08 — Missing or inconsistent input validation

<!-- WHAT: An unchecked boundary assumption. HOW: Compare expected input types,
limits and relationships with the operations that consume them. WHY: Presence
checks alone do not prevent type errors or invalid business state. -->

- **Default severity:** MEDIUM; increase only for a separately demonstrated higher-impact integrity/security consequence.
- **Detect:** `float()`/`int()` on unchecked query strings, comparisons or `len()` on unknown JSON types, `startsWith()` on an unvalidated value, negative quantities, invalid enum values, absent foreign records or create/update rules that disagree.
- **Confirm/evidence:** Show the accepted input source and failing conversion or missing invariant; reference a sanitized baseline case when available. Do not invent an HTTP result from source inspection alone.
- **False-positive guard:** Validation may occur in middleware, a schema or the called domain operation. ORM-bound `like()` expressions are not SQL injection merely because they accept text.
- **Impact:** Unexpected 500 responses, accepted invalid state or incompatible behavior across endpoints.
- **Correction:** Apply **AP-08**: validate boundary types and domain invariants, return appropriate 4xx responses and verify no unwanted writes for rejected input.

## AP-09 — Deprecated or legacy APIs

<!-- WHAT: Version-specific compatibility debt. HOW: Verify the exact symbol and
version against official documentation. WHY: A legacy coding style, a package's
age and a confirmed deprecated API are different claims. -->

- **Default severity:** MEDIUM for confirmed API deprecation; explain a higher/lower impact when the installed version or migration risk warrants it.
- **Detect:** Explicit deprecation warnings in existing evidence or calls documented as legacy/deprecated for the detected runtime/library version.
- **Confirm/evidence:** Record the exact symbol, source line, applicable runtime/library version, official documentation URL and recommended replacement. If only a version range is known, state the uncertainty rather than inventing an installed version.
- **Examples:** For applicable SQLAlchemy versions, `Model.query.get(id)` is a candidate for `session.get(Model, id)`. Python `datetime.utcnow()` is deprecated from Python 3.12; earlier runtimes must not be reported as emitting that version-specific deprecation.
- **False-positive guard:** Do not label `Buffer.from()` deprecated. Do not equate every legacy `Query` operation with a removed API. A replacement must preserve missing-record behavior, session semantics and timezone consistency.
- **Correction:** Apply **AP-09** after checking the version-specific [SQLAlchemy guidance](https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.get) or [Python datetime guidance](https://docs.python.org/3/library/datetime.html#datetime.datetime.utcnow). If documentation cannot be verified, leave the candidate unconfirmed.

## AP-10 — Scattered or unsafe error handling

<!-- WHAT: Inconsistent failure boundaries. HOW: Inspect propagation, cleanup and
public error payloads together. WHY: A centralized handler cannot catch an error
that an asynchronous callback never forwards to it. -->

- **Default severity:** MEDIUM for duplicated/inconsistent error responses; classify sensitive exception disclosure under AP-02 or broken atomicity under AP-14 when those mechanisms are established.
- **Detect:** Repeated broad catches returning raw exception strings, ignored database callback errors, missing rollback/cleanup, or thrown asynchronous errors that bypass the HTTP framework's error path.
- **Confirm/evidence:** Trace how a representative validation/data failure reaches the response or process boundary; identify status mapping, cleanup and sensitive output.
- **False-positive guard:** A broad catch at a deliberate outer boundary may be appropriate when it logs safely, cleans up and emits a sanitized response. Syntax alone does not establish poor handling.
- **Impact:** Inconsistent client contracts, lost diagnostics, incomplete cleanup or process crashes.
- **Correction:** Apply **AP-10**: use explicit application errors and a centralized boundary, forwarding asynchronous failures according to the detected framework/version.

## AP-11 — Ambiguous names

<!-- WHAT: Local naming debt. HOW: Follow a symbol through its scope before
renaming it. WHY: API field names and database columns may be contracts rather
than freely changeable implementation details. -->

- **Default severity:** LOW when the impact is readability.
- **Detect:** Single-letter or misleading business variables, generic helpers combining unrelated operations, or names that hide domain meaning in a complex workflow.
- **Confirm/evidence:** Cite the symbol and an ambiguous use; propose a concrete domain name and identify any external compatibility constraint.
- **False-positive guard:** Short loop indices, conventional mathematical variables and established framework parameter names can be clear in context.
- **Impact:** Slower comprehension and mistakes when modifying related values.
- **Correction:** Apply **AP-11**: rename internal symbols and their references while preserving public payload/schema names unless a contract change is approved.

## AP-12 — Magic values or dead code

<!-- WHAT: Unexplained policy values and unused implementation. HOW: Check
references and framework discovery before removal. WHY: Apparent unused code can
be reached dynamically, and ordinary numeric literals do not all need constants. -->

- **Default severity:** LOW for clarity/maintenance debt without a higher-impact defect.
- **Detect:** Repeated domain thresholds, percentages or enum strings with no named policy; duplicate literals despite existing constants; unused imports, exports, variables or unreachable helpers.
- **Confirm/evidence:** Show the repeated value and its business meaning, or the unused declaration plus a caller/reference search. Check reflective/framework registration before proposing deletion.
- **False-positive guard:** Obvious structural literals such as zero/one, cohesive local constants and intentionally public extension hooks do not establish a defect.
- **Impact:** Inconsistent rule changes, misleading code paths and unnecessary dependencies.
- **Correction:** Apply **AP-12**: name domain policy values in the appropriate layer and remove verified dead code without changing valid behavior.

## AP-13 — Missing authentication or authorization

<!-- WHAT: An unprotected action or resource boundary. HOW: Trace middleware and
ownership/role checks to the sensitive operation. WHY: A login endpoint, a token
string or an enum allowlist does not itself authorize subsequent actions. -->

- **Default severity:** HIGH; use CRITICAL for demonstrated destructive access, arbitrary data access or sensitive disclosure without authorization.
- **Detect:** Administrative/destructive handlers without access checks, client-supplied roles accepted as authority, predictable literal tokens, or operations using a client resource ID without checking ownership.
- **Confirm/evidence:** Inspect route registration, global middleware and service checks before concluding protection is absent. Cite the reachable sensitive action and missing/ineffective check; use prior anonymous-request evidence if available.
- **False-positive guard:** Deliberately public reads may be valid. Validation of a role string constrains syntax, not permission; authentication and authorization must be assessed separately.
- **Impact:** Privilege escalation, unauthorized modification/deletion or access to another user's data.
- **Correction:** Apply **AP-13**: establish trusted identity, enforce roles/ownership at the relevant boundary and validate allowed/denied flows as an intentional contract correction.

## AP-14 — Non-atomic writes or broken referential integrity

<!-- WHAT: A multi-write correctness boundary. HOW: Inspect transaction scope,
failure paths and relationship policy. WHY: A successful response alone cannot
prove stock, totals and linked records remained consistent. -->

- **Default severity:** HIGH when partial writes or orphaned records can corrupt a normal business workflow.
- **Detect:** Multiple dependent inserts/updates committed independently, inventory changed before later validation, missing rollback, or deletion of a parent without a defined dependent-record policy.
- **Confirm/evidence:** Map the intended unit of work and its failure points; inspect transaction ownership, constraints and cascade/restrict behavior. Distinguish confirmed partial writes from a static risk needing later execution evidence.
- **False-positive guard:** Autocommit is acceptable for independent writes. External effects cannot be rolled back with a local SQL transaction; identify an appropriate coordination strategy instead of promising impossible atomicity.
- **Impact:** Orphaned relationships, inconsistent revenue/stock and misleading success or failure responses.
- **Correction:** Apply **AP-14**: choose explicit transaction and relationship boundaries, validate before writing and test failure-path state in an isolated database after approval.
