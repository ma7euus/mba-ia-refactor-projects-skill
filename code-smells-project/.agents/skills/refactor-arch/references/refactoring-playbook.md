# Refactoring playbook

<!-- WHAT: This is the Phase 3 transformation reference. HOW: Match confirmed catalog
IDs to examples and load only relevant sections. WHY: Lessons 2, 8 and 10 put detailed
knowledge in progressive-disclosure level 3 while keeping SKILL.md procedural. -->

Use after approval of the Phase 2 report. Match findings from [the catalog](anti-patterns.md)
to the transformations below and follow [the MVC boundaries](mvc-guidelines.md).
The examples use generic domains, not mandatory filenames or dependencies. Adapt
driver placeholders, response fields and wiring to the detected stack and approved
contract. Framework objects and mapped ORM classes come from the surrounding
application; each section states its additional dependency contracts.

| ID | Transformation | Example stack |
|---|---|---|
| AP-01 | Parameterize SQL | Python / SQLite |
| AP-02 | Externalize configuration and reduce output | Python / Flask |
| AP-03 | Split a God Module | JavaScript / Express |
| AP-04 | Extract domain rules from handlers | Python / Flask |
| AP-05 | Replace insecure password storage | Python / Werkzeug |
| AP-06 | Give dependencies an explicit lifetime | Python / Flask |
| AP-07 | Batch relationship queries | Python / SQLAlchemy |
| AP-08 | Validate types and limits | Python |
| AP-09 | Replace a confirmed legacy API | Python / SQLAlchemy |
| AP-10 | Forward and centralize errors | JavaScript / Express |
| AP-11 | Clarify local names | JavaScript |
| AP-12 | Name constants and remove dead code | Python |
| AP-13 | Enforce authorization | JavaScript / Express |
| AP-14 | Make related writes atomic | Python / SQLite |

## AP-01 — Parameterize SQL
<!-- WHAT: Separate SQL structure from values. HOW: Bind values through the actual
driver. WHY: Manual escaping is fragile; a routed integer alone is not proof of injection. -->

Apply to client values interpolated into SQL. Here `db` is an existing SQLite connection.
**Before**
```python
def find_by_email(db, email):
    sql = f"SELECT id, email FROM users WHERE email = '{email}'"
    return db.execute(sql).fetchone()
```
**After**
```python
def find_by_email(db, email):
    return db.execute(
        "SELECT id, email FROM users WHERE email = ?", (email,)
    ).fetchone()
```
Verify ordinary values, no match and a legitimate apostrophe. Preserve result shape
and absence semantics. Other drivers may use different placeholders. Bound values
cannot replace SQL identifiers: map permitted sort fields to known identifiers.

## AP-02 — Externalize configuration and reduce output
<!-- WHAT: Remove embedded secrets and output leaks. HOW: Read configuration at
composition time and select public output fields. WHY: Environment variables alone
do not fix a serializer or logging leak. -->

Apply to embedded configuration or sensitive output. Here `app` is the Flask app.
**Before**
```python
app.config["SECRET_KEY"] = "example-only-hardcoded-value"

@app.get("/health")
def health():
    return {"status": "ok", "secret_key": app.config["SECRET_KEY"]}
```
**After**
```python
import os

app.config["SECRET_KEY"] = os.environ["APP_SECRET_KEY"]

@app.get("/health")
def health():
    return {"status": "ok"}
```
Document required variable names with dummy examples and supply them for boot checks;
do not replace a secret with another embedded default. Explicitly select public user
fields and redact passwords, hashes, tokens, payment data and credentials in logs.
Test output absence and document removed fields as approved contract corrections.

## AP-03 — Split a God Module
<!-- WHAT: Separate HTTP flow and persistence. HOW: Inject a model into a controller
and wire routes at the composition root. WHY: New folders alone do not create boundaries. -->

Here `app` is Express and `db.get(sql, parameters, callback)` is the existing driver API.
**Before**
```javascript
class Manager {
  constructor(db) { this.db = db; }
  register(app) {
    app.get('/items/:id', (req, res, next) => {
      this.db.get('SELECT id, name FROM items WHERE id = ?', [req.params.id],
        (error, row) => error ? next(error) : res.json(row));
    });
  }
}
```
**After**
```javascript
function createItemModel(db) {
  return { findById(id, callback) {
    db.get('SELECT id, name FROM items WHERE id = ?', [id], callback);
  } };
}
function createItemController(model) {
  return { get(id, callback) {
    model.findById(id, callback);
  } };
}
const controller = createItemController(createItemModel(db));
app.get('/items/:id', (req, res, next) => {
  controller.get(req.params.id, (error, row) => {
    if (error) return next(error);
    return res.json(row);
  });
});
```
Split declarations into model, controller and route modules. This structural example
preserves existing response behavior; correct missing-record handling if approved.
Test route behavior, persistence and startup after each move; update all import paths.

## AP-04 — Extract domain rules from handlers
<!-- WHAT: Make domain calculations independent of HTTP. HOW: Extract rules and let
controllers coordinate persistence. WHY: Putting all business logic into a controller
recreates the smell under a different name. -->

Here `order_model.create(total=...)` is an injected persistence contract returning a
serializable result. Lines must already pass input validation as described in AP-08.
**Before**
```python
@app.post("/orders")
def create_order_route():
    lines = request.get_json()["lines"]
    total = sum(line["price"] * line["quantity"] for line in lines)
    return jsonify(order_model.create(total=total)), 201
```
**After**
```python
def calculate_total(lines):
    return sum(line["price"] * line["quantity"] for line in lines)

def create_order_controller(lines, model):
    return model.create(total=calculate_total(lines))

@app.post("/orders")
def create_order_route():
    lines = request.get_json()["lines"]
    return jsonify(create_order_controller(lines, order_model)), 201
```
Place calculation in the domain/model layer, coordination in the controller and HTTP
adaptation in routes/views. Compare totals and writes with the baseline; do not change
rounding or currency representation incidentally.

## AP-05 — Replace insecure password storage
<!-- WHAT: Replace plaintext or homemade hashing. HOW: Use a password library's paired
generate/verify APIs. WHY: Storage changes need migration so existing users retain access. -->

Apply to plaintext, MD5 or reversible encoding. Verify the installed library's support.
**Before**
```python
def encode_password(password):
    return password

def verify_password(stored, candidate):
    return stored == candidate
```
**After**
```python
from werkzeug.security import check_password_hash, generate_password_hash

def encode_password(password):
    return generate_password_hash(password)

def verify_password(stored, candidate):
    return check_password_hash(stored, candidate)
```
Migrate confirmed plaintext in a controlled migration. For existing one-way hashes,
use an approved reset or verified-login upgrade strategy; never hash an old digest
as if it were the original password. Preserve IDs and test migrated users, invalid
passwords and output redaction. Do not reset a user's database to simplify migration.

## AP-06 — Give mutable dependencies an explicit lifetime
<!-- WHAT: Remove an implicitly shared connection. HOW: Scope SQLite to the Flask
application context and close on teardown. WHY: Ownership prevents request interference. -->

Here `app` is the composition-root Flask app and `DATABASE` identifies the existing DB.
**Before**
```python
import sqlite3

connection = sqlite3.connect("application.db", check_same_thread=False)
def get_db():
    return connection
```
**After**
```python
import sqlite3
from flask import current_app, g

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()
```
Resolve the database path explicitly; changing relative paths can create an empty DB.
Run schema bootstrap inside an application context where required. Test independent
requests and cleanup; retain transaction semantics. Other stacks may use injected pools.

## AP-07 — Batch relationship queries
<!-- WHAT: Remove per-record relationship reads. HOW: Use ORM loading or a measured
join. WHY: Equivalent results and measured query growth demonstrate removal of N+1. -->

Here `Order.lines` is an existing mapped relationship; `consume(order, lines)` is the
unchanged presentation operation and `session` is the existing ORM session.
**Before**
```python
from sqlalchemy import select

orders = session.scalars(select(Order)).all()
for order in orders:
    lines = session.scalars(select(Line).where(Line.order_id == order.id)).all()
    consume(order, lines)
```
**After**
```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

orders = session.scalars(select(Order).options(selectinload(Order.lines))).all()
for order in orders:
    consume(order, order.lines)
```
Measure query growth for many records and empty relationships; compare IDs, totals
and ordering. Loading can use several batches: do not promise an unconditional two-query
limit or change pagination without approval. For an application using raw SQLite,
keep that driver and batch with joins or grouped reads instead of adding an ORM
just to copy this example.

## AP-08 — Validate types and domain limits
<!-- WHAT: Reject malformed input before writes. HOW: Check container and field types
before comparisons. WHY: Presence checks miss TypeError; booleans are also Python ints. -->

Map `InputError` to a centralized 400 response in the detected framework.
**Before**
```python
def read_quantity(payload):
    quantity = payload["quantity"]
    if quantity < 1:
        raise ValueError("Quantity must be positive")
    return quantity
```
**After**
```python
class InputError(ValueError):
    pass

def read_quantity(payload):
    if not isinstance(payload, dict):
        raise InputError("Expected a JSON object")
    quantity = payload.get("quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        raise InputError("Quantity must be a positive integer")
    return quantity
```
Verify missing, null, boolean, string, object, zero, negative and valid values; assert
4xx and no persistence changes for rejection. Preserve deliberately supported coercions
and query-string parsing where the approved contract requires them.

## AP-09 — Replace a confirmed legacy API
<!-- WHAT: Migrate a version-confirmed obsolete API. HOW: Preserve optional lookup
semantics. WHY: Replacing every lookup with get-or-404 changes legitimate control flow. -->

Confirm `Query.get()` is legacy for the installed SQLAlchemy version. Here `session`
is an existing session and `User` an existing mapped model.
**Before**
```python
def optional_user(user_id):
    return User.query.get(user_id)
```
**After**
```python
def optional_user(user_id):
    return session.get(User, user_id)
```
Verify existing and missing IDs, including `None`; return 404 only where the route
contract requires it. Cite the matching-version [official documentation](https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.get).
For `datetime.utcnow()`, first confirm Python 3.12+ deprecation and review storage,
comparisons and serialization together; changing only one side to aware dates can break it.

## AP-10 — Forward and centralize errors
<!-- WHAT: Route async failures to one HTTP boundary. HOW: Wrap promises and register
error middleware last. WHY: Express 4 needs rejections forwarded through next. -->

Here injected `controller.findById(id)` returns a promise of public data and
coordinates the domain/model layer without reading HTTP objects. Known application
errors use a shared `ApplicationError` type and fixed public error codes.
**Before**
```javascript
app.get('/items/:id', async (req, res) => {
  res.json(await controller.findById(req.params.id));
});
```
**After**
```javascript
class ApplicationError extends Error {
  constructor(code) { super(code); this.code = code; }
}
const publicErrors = new Map([
  ['INVALID_INPUT', { status: 400, message: 'Invalid request' }],
  ['NOT_FOUND', { status: 404, message: 'Resource not found' }],
  ['CONFLICT', { status: 409, message: 'Conflicting operation' }],
]);
const asyncRoute = handler => (req, res, next) =>
  Promise.resolve().then(() => handler(req, res, next)).catch(next);

app.get('/items/:id', asyncRoute(async (req, res) => {
  res.json(await controller.findById(req.params.id));
}));
app.use((error, req, res, next) => {
  if (res.headersSent) return next(error);
  const known = error instanceof ApplicationError ? publicErrors.get(error.code) : null;
  const malformedJson = error.type === 'entity.parse.failed' && error.status === 400;
  const response = known || (malformedJson
    ? { status: 400, message: 'Invalid JSON' }
    : { status: 500, message: 'Internal error' });
  res.status(response.status).json({ error: response.message });
});
```
Export the shared error type for controllers/domain adapters. Adapt its allowlisted
codes and verified parser error mapping to the installed framework and approved
contract; never trust arbitrary `error.status` or expose arbitrary error messages.
Callback APIs must call `next(error)` inside callbacks: this wrapper cannot catch
unrelated later throws. Test callback/promise failures, malformed JSON, missing
records, invalid error statuses and redacted internal errors.

## AP-11 — Clarify names without changing wire contracts
<!-- WHAT: Make local symbols express intent. HOW: Rename callers but retain public
fields. WHY: A readability fix does not authorize renaming clients' request properties. -->

Here incoming field `p` is an existing serialized contract.
**Before**
```javascript
function sum(e) {
  return e.reduce((t, c) => t + c.p, 0);
}
```
**After**
```javascript
function totalEnrollmentPrice(enrollments) {
  return enrollments.reduce((total, enrollment) => total + enrollment.p, 0);
}
```
Update imports and calls. Compare empty/populated results and verify that route paths
and JSON property names did not change accidentally.

## AP-12 — Name constants and remove dead code
<!-- WHAT: Reveal business rules and remove confirmed unused state. HOW: Name repeated
values and inspect callers before deletion. WHY: Exported symbols may have consumers. -->

Preserve the formula and numeric representation during this readability change.
**Before**
```python
unused_total = 0

def discounted_total(total):
    return total * 0.95 if total >= 1000 else total
```
**After**
```python
BULK_DISCOUNT_THRESHOLD = 1000
BULK_DISCOUNT_MULTIPLIER = 0.95

def discounted_total(total):
    if total >= BULK_DISCOUNT_THRESHOLD:
        return total * BULK_DISCOUNT_MULTIPLIER
    return total
```
Search references before removing exported code. Verify immediately below, at and
above the threshold; retain rounding unless its correction was independently approved.

## AP-13 — Enforce authorization at the HTTP boundary
<!-- WHAT: Protect privileged routes. HOW: Authenticate, then check a server-sourced
role. WHY: A client-provided role or token-shaped string is not a trusted identity. -->

Here `authenticate` is an injected middleware contract: verify the configured
session/token, reject invalid identities and populate `req.user` from trusted data.
`controller.deleteUser` is the existing deletion flow. Do not replace authentication
with fake tokens or trust identity/role fields in public JSON.
**Before**
```javascript
function registerUserRoutes(app, controller) {
  app.delete('/users/:id', controller.deleteUser);
}
```
**After**
```javascript
function registerUserRoutes(app, authenticate, controller) {
  const requireAdmin = (req, res, next) => {
    if (!req.user) return res.status(401).json({ error: 'Authentication required' });
    if (req.user.role !== 'admin') return res.status(403).json({ error: 'Forbidden' });
    return next();
  };
  app.delete('/users/:id', authenticate, requireAdmin, controller.deleteUser);
}
```
If real authentication is absent, propose its design or an approved restriction;
do not claim this middleware completes that integration. Test anonymous, invalid,
expired, non-admin and allowed-admin cases with no unauthorized writes. For raw-SQL
administration, replace unrestricted SQL with approved bounded operations as well.

## AP-14 — Make related writes atomic
<!-- WHAT: Preserve invariants across related writes. HOW: Use one transaction,
guarded stock updates and rollback. WHY: Compensation after partial commit is not atomic. -->

Here `db` uses SQLite legacy transaction control, a non-None `isolation_level` and
no active outer transaction. This function owns commit/rollback. The example tables
already exist with the shown columns. For caller-owned transactions, use a savepoint
or the existing unit of work rather than committing the caller's transaction.
**Before**
```python
def reserve(db, item_id, quantity):
    db.execute("UPDATE items SET stock = stock - ? WHERE id = ?", (quantity, item_id))
    db.commit()
    cursor = db.execute(
        "INSERT INTO reservations (item_id, quantity) VALUES (?, ?)",
        (item_id, quantity),
    )
    db.commit()
    return cursor.lastrowid
```
**After**
```python
class ReservationError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code

def reserve(db, item_id, quantity):
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        raise ReservationError("INVALID_QUANTITY")
    if db.in_transaction or db.isolation_level is None or getattr(db, "autocommit", None) is True:
        raise RuntimeError("This operation requires ownership of a transactional connection")
    with db:
        updated = db.execute(
            "UPDATE items SET stock = stock - ? WHERE id = ? AND stock >= ?",
            (quantity, item_id, quantity),
        )
        if updated.rowcount != 1:
            raise ReservationError("UNAVAILABLE_ITEM")
        cursor = db.execute(
            "INSERT INTO reservations (item_id, quantity) VALUES (?, ?)",
            (item_id, quantity),
        )
    return cursor.lastrowid
```
Verify success, insufficient stock, negative quantity and a forced insert failure
with stock unchanged after rollback. Translate `INVALID_QUANTITY` to the approved
400 response and `UNAVAILABLE_ITEM` to the approved conflict/not-found response;
do not let expected domain rejections fall through as generic 500 errors. Verify
the connection's transaction mode; a context manager in autocommit mode is not a
transaction. Configure and test foreign keys with an explicit migration for existing
orphans. External payments/messages need an approved idempotency or outbox design:
rolling back a database cannot undo an external side effect.

## Incremental execution and final validation
<!-- WHAT: Establish evidence of a working MVC application. HOW: Verify each changed
domain, then replay the endpoint baseline against the new code. WHY: Lessons 11, 12
and 14 distinguish a planned change from a verified result. -->

1. Preserve the approved pre-refactoring report and its original file/line evidence.
2. Implement a coherent domain slice, including imports and dependency wiring.
3. Run existing or focused integration checks and fix introduced failures before
   moving to another slice. Use disposable fixtures, not the user's live database.
4. Boot the final app with documented configuration and exercise every original
   method/route combination, valid/rejected cases and persistence effects.
5. Compare the baseline with preserved valid behavior and approved security/integrity
   corrections. Check response fields, stored totals, stock, relationships and rollback.
6. Revisit every finding and record its new location, status and validation evidence.
   Report remaining failures; startup alone does not establish zero anti-patterns.

An existing baseline runner may intentionally load the historical commit. Use that
runner for legacy evidence; run separate checks against the refactored working tree
before claiming success. A passing replay of old code cannot validate new edits.
