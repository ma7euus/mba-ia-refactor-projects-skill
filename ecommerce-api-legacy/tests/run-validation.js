'use strict';

// Run the current working tree, with real HTTP and fresh in-memory databases.
// Synthetic credentials and raw database snapshots never enter the evidence.
const assert = require('node:assert/strict');
const { randomBytes, createHash } = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { once } = require('node:events');
const { createApplication } = require('../src/app');
const { loadConfig } = require('../src/config');
const passwords = require('../src/services/passwords');
const reports = require('../src/models/reports');

const projectRoot = path.resolve(__dirname, '..');
const tableNames = ['users', 'courses', 'enrollments', 'payments', 'audit_logs'];
const operations = [
  ['POST', '/api/checkout'],
  ['GET', '/api/admin/financial-report'],
  ['DELETE', '/api/users/:id'],
];
const secret = () => randomBytes(32).toString('hex');
const adminToken = secret();
const password = secret();
const demoPassword = secret();
const card = `4-synthetic-${randomBytes(16).toString('hex')}`;
const deniedCard = `5-synthetic-${randomBytes(16).toString('hex')}`;
const wrongPassword = secret();
const logs = [];
const logger = Object.fromEntries(['info', 'warn', 'error', 'log'].map(level => [
  level, (...values) => logs.push({ level, values }),
]));
const evidence = {
  project: 'ecommerce-api-legacy',
  timestamp: new Date().toISOString(),
  sourceTarget: 'current-working-tree',
  isolation: 'fresh SQLite :memory: per application; synthetic fixtures; loopback HTTP',
  environment: {
    node: process.version,
    express: require('express/package.json').version,
    sqlite3: require('sqlite3/package.json').version,
  },
  sourceHashes: {},
  operations: operations.map(([method, route]) => ({ method, route })),
  scenarios: [],
  measurements: {},
  limits: [
    'Operation coverage is not line coverage or a load test.',
    'Payments remain simulated; no gateway, real card or external notification is used.',
    'The default database remains ephemeral; no persistent-data migration is claimed.',
  ],
};

function sourceHashes(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const filename = path.join(directory, entry.name);
    if (entry.isDirectory()) sourceHashes(filename);
    else if (entry.name.endsWith('.js')) {
      evidence.sourceHashes[path.relative(projectRoot, filename)] = createHash('sha256')
        .update(fs.readFileSync(filename)).digest('hex');
    }
  }
}

async function scenario(id, name, action) {
  const started = performance.now();
  try {
    const details = await action();
    const result = { id, name, passed: true, ...details };
    result.durationMs = Math.round(performance.now() - started);
    evidence.scenarios.push(result);
    process.stderr.write(`PASS ${id} ${name}\n`);
  } catch (error) {
    // Assertion diffs can contain passwords/hashes. Export only the error type.
    evidence.scenarios.push({ id, name, passed: false, failureType: error.name });
    process.stderr.write(`FAIL ${id} ${name} (${error.name})\n`);
    throw new Error(`Validation stopped at ${id}`);
  }
}

async function startApplication(config) {
  const application = await createApplication({ config, logger });
  let server;
  try {
    server = application.app.listen(0, '127.0.0.1');
    await once(server, 'listening');
  } catch (error) {
    await application.close();
    throw error;
  }
  return {
    ...application,
    baseUrl: `http://127.0.0.1:${server.address().port}`,
    async shutdown() {
      await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
      await application.close();
    },
  };
}

async function request(application, method, route, { payload, raw, authorized = false, token, headers = {} } = {}) {
  const requestHeaders = { ...headers };
  if (authorized || token !== undefined) requestHeaders.Authorization = `Bearer ${token ?? adminToken}`;
  let body;
  if (raw !== undefined) {
    requestHeaders['Content-Type'] ??= 'application/json';
    body = raw;
  } else if (payload !== undefined) {
    requestHeaders['Content-Type'] ??= 'application/json';
    body = JSON.stringify(payload);
  }
  const response = await fetch(application.baseUrl + route, {
    method, headers: requestHeaders, body, signal: AbortSignal.timeout(10000),
  });
  const text = await response.text();
  let parsed = text;
  if (response.headers.get('content-type')?.includes('application/json')) parsed = JSON.parse(text);
  return { status: response.status, body: parsed, text, headers: response.headers };
}

function checkout(overrides = {}) {
  return { usr: 'Validation Paid Student', eml: 'validation-paid@example.test', pwd: password, c_id: 1, card, ...overrides };
}

function revenue(report) {
  return report.reduce((total, course) => total + course.revenue, 0);
}

function assertReportShape(report) {
  assert.ok(Array.isArray(report));
  for (const course of report) {
    assert.deepEqual(Object.keys(course).sort(), ['course', 'revenue', 'students']);
    assert.equal(typeof course.course, 'string');
    assert.equal(typeof course.revenue, 'number');
    assert.ok(Array.isArray(course.students));
    for (const student of course.students) {
      assert.deepEqual(Object.keys(student).sort(), ['paid', 'student']);
    }
  }
}

async function snapshot(database) {
  return database.exclusive(async db => {
    const result = {};
    for (const table of tableNames) result[table] = await db.all(`SELECT * FROM ${table} ORDER BY id`);
    return result;
  });
}

function counts(state) {
  return Object.fromEntries(tableNames.map(table => [table, state[table].length]));
}

async function unchanged(application, action) {
  const before = await snapshot(application.database);
  const result = await action();
  assert.deepEqual(await snapshot(application.database), before, 'Rejected operation changed stored records');
  return result;
}

async function baseline(application) {
  let enrollmentId;
  let userId;
  await scenario('P2-01', 'Relatório inicial autorizado, cursos e seed equivalentes', async () => {
    const result = await request(application, 'GET', '/api/admin/financial-report', { authorized: true });
    assert.equal(result.status, 200);
    assertReportShape(result.body);
    assert.equal(result.body.length, 2);
    assert.equal(revenue(result.body), 997);
    const state = await snapshot(application.database);
    assert.deepEqual(counts(state), { users: 1, courses: 2, enrollments: 1, payments: 1, audit_logs: 0 });
    assert.ok(result.body.some(course => course.students.length === 0));
    evidence.environment.sqlite = (await application.database.exclusive(db => db.get('SELECT sqlite_version() AS version'))).version;
    return { status: result.status, revenue: 997, counts: counts(state) };
  });
  await scenario('P2-02', 'Checkout novo persiste usuário, matrícula, pagamento e auditoria', async () => {
    const before = counts(await snapshot(application.database));
    const result = await request(application, 'POST', '/api/checkout', { payload: checkout() });
    assert.equal(result.status, 200);
    assert.deepEqual(Object.keys(result.body).sort(), ['enrollment_id', 'msg']);
    assert.equal(result.body.msg, 'Sucesso');
    enrollmentId = result.body.enrollment_id;
    assert.ok(Number.isSafeInteger(enrollmentId));
    const state = await snapshot(application.database);
    for (const table of ['users', 'enrollments', 'payments', 'audit_logs']) assert.equal(state[table].length, before[table] + 1);
    const payment = state.payments.find(row => row.enrollment_id === enrollmentId);
    assert.equal(payment.status, 'PAID');
    assert.equal(payment.amount, 997);
    userId = state.users.find(user => user.email === checkout().eml).id;
    return { status: result.status, paymentStatus: payment.status, amount: payment.amount };
  });
  await scenario('P2-03', 'Relatório após checkout conserva formato, aluno e receita', async () => {
    const result = await request(application, 'GET', '/api/admin/financial-report', { authorized: true });
    assert.equal(result.status, 200);
    assertReportShape(result.body);
    assert.equal(revenue(result.body), 1994);
    assert.equal(result.body.flatMap(course => course.students).filter(student => student.student === checkout().usr).length, 1);
    return { status: result.status, revenue: 1994 };
  });
  await scenario('P2-04', 'Senha válida reutiliza conta no segundo curso', async () => {
    const before = counts(await snapshot(application.database));
    const result = await request(application, 'POST', '/api/checkout', { payload: checkout({ c_id: 2 }) });
    assert.equal(result.status, 200);
    const after = counts(await snapshot(application.database));
    assert.equal(after.users, before.users);
    for (const table of ['enrollments', 'payments', 'audit_logs']) assert.equal(after[table], before[table] + 1);
    const report = await request(application, 'GET', '/api/admin/financial-report', { authorized: true });
    assert.equal(revenue(report.body), 2491);
    return { status: result.status, revenue: 2491, duplicatedUsers: 0 };
  });
  await scenario('P2-05', 'Pagamento recusado retorna 400 sem qualquer gravação', async () => {
    const result = await unchanged(application, () => request(application, 'POST', '/api/checkout', {
      payload: checkout({ eml: 'validation-denied@example.test', card: deniedCard }),
    }));
    assert.equal(result.status, 400);
    assert.equal(result.body, 'Pagamento recusado');
    return { status: result.status, allStoredFieldsUnchanged: true };
  });
  await scenario('P2-06', 'Campos obrigatórios ausentes são rejeitados', async () => {
    const result = await unchanged(application, () => request(application, 'POST', '/api/checkout', { payload: { usr: 'Missing' } }));
    assert.equal(result.status, 400);
    return { status: result.status, allStoredFieldsUnchanged: true };
  });
  await scenario('P2-07', 'Curso inexistente retorna 404 sem gravações', async () => {
    const result = await unchanged(application, () => request(application, 'POST', '/api/checkout', { payload: checkout({ c_id: 999999 }) }));
    assert.equal(result.status, 404);
    return { status: result.status, allStoredFieldsUnchanged: true };
  });
  await scenario('P2-08', 'Cadastro sem senha é rejeitado', async () => {
    const payload = checkout({ eml: 'validation-no-password@example.test' });
    delete payload.pwd;
    const result = await unchanged(application, () => request(application, 'POST', '/api/checkout', { payload }));
    assert.equal(result.status, 400);
    return { status: result.status, allStoredFieldsUnchanged: true };
  });
  await scenario('P2-09', 'Email malformado é rejeitado antes da persistência', async () => {
    const result = await unchanged(application, () => request(application, 'POST', '/api/checkout', { payload: checkout({ eml: 'invalid-email' }) }));
    assert.equal(result.status, 400);
    return { status: result.status, allStoredFieldsUnchanged: true };
  });
  await scenario('P2-10', 'Relatório administrativo anônimo é negado', async () => {
    const result = await unchanged(application, () => request(application, 'GET', '/api/admin/financial-report'));
    assert.equal(result.status, 401);
    assert.ok(result.headers.get('www-authenticate'));
    return { status: result.status, allStoredFieldsUnchanged: true };
  });
  await scenario('P2-11', 'Exclusão de usuário matriculado é impedida sem órfãos', async () => {
    const result = await unchanged(application, () => request(application, 'DELETE', `/api/users/${userId}`, { authorized: true }));
    assert.equal(result.status, 409);
    const orphans = await application.database.exclusive(db => db.all('PRAGMA foreign_key_check'));
    assert.deepEqual(orphans, []);
    return { status: result.status, allStoredFieldsUnchanged: true, foreignKeyViolations: 0 };
  });
  await scenario('P2-12', 'Relatório mantém receita e alunos após exclusão impedida', async () => {
    const result = await request(application, 'GET', '/api/admin/financial-report', { authorized: true });
    assert.equal(result.status, 200);
    assert.equal(revenue(result.body), 2491);
    assert.ok(result.body.flatMap(course => course.students).every(student => student.student !== 'Unknown'));
    return { status: result.status, revenue: 2491, unknownStudents: 0 };
  });
  await scenario('P2-13', 'Exclusão de usuário inexistente retorna 404', async () => {
    const result = await unchanged(application, () => request(application, 'DELETE', '/api/users/999999', { authorized: true }));
    assert.equal(result.status, 404);
    return { status: result.status, allStoredFieldsUnchanged: true };
  });
  await scenario('P2-14', 'Cartão numérico retorna 400 e servidor continua disponível', async () => {
    const result = await unchanged(application, () => request(application, 'POST', '/api/checkout', { payload: checkout({ card: 4 }) }));
    assert.equal(result.status, 400);
    const recovery = await request(application, 'GET', '/api/admin/financial-report', { authorized: true });
    assert.equal(recovery.status, 200);
    return { status: result.status, subsequentRequestStatus: recovery.status, allStoredFieldsUnchanged: true };
  });
}

async function extended(application) {
  await scenario('AUTH-01', 'Token administrativo incorreto não permite ler ou excluir', async () => {
    const invalidToken = secret();
    for (const [method, route] of [['GET', '/api/admin/financial-report'], ['DELETE', '/api/users/1']]) {
      const result = await unchanged(application, () => request(application, method, route, { token: invalidToken }));
      assert.equal(result.status, 401);
    }
    return { statuses: [401, 401], allStoredFieldsUnchanged: true };
  });
  await scenario('AUTH-02', 'Exclusão anônima é negada', async () => {
    const result = await unchanged(application, () => request(application, 'DELETE', '/api/users/1'));
    assert.equal(result.status, 401);
    return { status: result.status, allStoredFieldsUnchanged: true };
  });
  await scenario('AUTH-03', 'Email existente exige senha correta', async () => {
    const wrong = await unchanged(application, () => request(application, 'POST', '/api/checkout', { payload: checkout({ pwd: wrongPassword }) }));
    assert.equal(wrong.status, 401);
    const payload = checkout();
    delete payload.pwd;
    const missing = await unchanged(application, () => request(application, 'POST', '/api/checkout', { payload }));
    assert.equal(missing.status, 400);
    return { incorrectPasswordStatus: 401, missingPasswordStatus: 400, allStoredFieldsUnchanged: true };
  });
  await scenario('INPUT-01', 'JSON malformado, ausente e estruturas inválidas retornam 400', async () => {
    const requests = [
      { raw: '{"usr":' }, { raw: 'null' }, { raw: '[]' }, { raw: 'true' }, { raw: '"text"' }, {},
    ];
    for (const options of requests) {
      const result = await unchanged(application, () => request(application, 'POST', '/api/checkout', options));
      assert.equal(result.status, 400);
    }
    return { rejectedCases: requests.length, status: 400, allStoredFieldsUnchanged: true };
  });
  await scenario('INPUT-02', 'Tipos e limites de campos são validados', async () => {
    const invalidFields = [
      { usr: '' }, { usr: {} }, { usr: 'x'.repeat(201) },
      { eml: null }, { eml: [] }, { eml: 'missing-at.test' },
      { pwd: '' }, { pwd: 123 }, { pwd: 'x'.repeat(1025) }, { pwd: 'é'.repeat(513) },
      { c_id: 0 }, { c_id: -1 }, { c_id: 1.2 }, { c_id: true }, { c_id: {} },
      { card: '' }, { card: null }, { card: [] }, { card: {} }, { card: '4'.repeat(65) },
    ];
    for (const invalid of invalidFields) {
      const result = await unchanged(application, () => request(application, 'POST', '/api/checkout', { payload: checkout(invalid) }));
      assert.equal(result.status, 400);
    }
    return { rejectedCases: invalidFields.length, status: 400, allStoredFieldsUnchanged: true };
  });
  await scenario('INPUT-03', 'Identificadores inválidos na exclusão são rejeitados', async () => {
    for (const id of ['0', '-1', '1.5', 'abc', '9007199254740992']) {
      const result = await unchanged(application, () => request(application, 'DELETE', `/api/users/${id}`, { authorized: true }));
      assert.equal(result.status, 400);
    }
    return { rejectedCases: 5, status: 400, allStoredFieldsUnchanged: true };
  });
  await scenario('INPUT-04', 'Curso inativo não aceita checkout', async () => {
    const courseId = await application.database.transaction(async db => {
      const result = await db.run('INSERT INTO courses(title, price, active) VALUES (?, ?, ?)', ['Inactive fixture', 1, 0]);
      return result.lastID;
    });
    const result = await unchanged(application, () => request(application, 'POST', '/api/checkout', { payload: checkout({ c_id: courseId }) }));
    assert.equal(result.status, 404);
    return { status: result.status, allStoredFieldsUnchanged: true };
  });
  await scenario('INPUT-05', 'URI inválida, charset e payload excessivo têm erros controlados', async () => {
    const uri = await unchanged(application, () => request(application, 'DELETE', '/api/users/%E0%A4%A', { authorized: true }));
    assert.equal(uri.status, 400);
    const charset = await unchanged(application, () => request(application, 'POST', '/api/checkout', {
      raw: '{}', headers: { 'Content-Type': 'application/json; charset=unsupported-charset' },
    }));
    assert.equal(charset.status, 415);
    const large = await unchanged(application, () => request(application, 'POST', '/api/checkout', {
      payload: checkout({ usr: 'x'.repeat(17000) }),
    }));
    assert.equal(large.status, 413);
    return { invalidUriStatus: 400, unsupportedCharsetStatus: 415, oversizedPayloadStatus: 413, allStoredFieldsUnchanged: true };
  });
  await scenario('CONFIG-01', 'Configuração valida limites e exige senha explícita para seed', async () => {
    const defaults = loadConfig({});
    assert.equal(defaults.host, '127.0.0.1');
    assert.equal(defaults.port, 3000);
    assert.equal(defaults.seedDemo, false);
    assert.equal(defaults.adminToken, undefined);
    for (const invalid of [
      { PORT: '-1' }, { PORT: '65536' }, { PORT: 'abc' },
      { HOST: ' ' }, { SEED_DEMO_DATA: 'true' },
      { SEED_DEMO_DATA: '1' }, { SEED_DEMO_DATA: '1', DEMO_USER_PASSWORD: ' ' },
      { SEED_DEMO_DATA: '1', DEMO_USER_PASSWORD: 'é'.repeat(513) },
      { ADMIN_API_TOKEN: 'short' }, { ADMIN_API_TOKEN: ' '.repeat(32) },
    ]) assert.throws(() => loadConfig(invalid));
    const configured = loadConfig({ PORT: '0', SEED_DEMO_DATA: '1', DEMO_USER_PASSWORD: demoPassword, ADMIN_API_TOKEN: adminToken });
    assert.equal(configured.port, 0);
    assert.equal(configured.seedDemo, true);
    return { rejectedConfigurations: 10, explicitDemoConfigAccepted: true, safeDefaults: true };
  });
  await scenario('DELETE-01', 'Administrador exclui usuário sem dependências', async () => {
    const hash = await passwords.hash(password);
    const id = await application.database.transaction(async db => {
      const result = await db.run('INSERT INTO users(name, email, pass) VALUES (?, ?, ?)', ['Removable fixture', 'removable@example.test', hash]);
      return result.lastID;
    });
    const before = await snapshot(application.database);
    const result = await request(application, 'DELETE', `/api/users/${id}`, { authorized: true });
    assert.equal(result.status, 200);
    const after = await snapshot(application.database);
    assert.deepEqual(after.users, before.users.filter(user => user.id !== id));
    for (const table of tableNames.filter(table => table !== 'users')) assert.deepEqual(after[table], before[table]);
    return { status: result.status, removedUsers: 1, otherStoredFieldsUnchanged: true };
  });
  await scenario('PASSWORD-01', 'Hashes usam salt, verificam senhas e seed não guarda texto', async () => {
    const first = await passwords.hash(password);
    const second = await passwords.hash(password);
    assert.notEqual(first, second, 'Independent salts must produce different hashes');
    assert.ok(first !== password);
    assert.ok(await passwords.verify(first, password));
    assert.ok(!await passwords.verify(first, wrongPassword));
    assert.ok(!await passwords.verify('invalid-stored-format', password));
    const seed = await application.database.exclusive(db => db.get('SELECT pass FROM users WHERE id = 1'));
    assert.ok(seed.pass !== demoPassword);
    assert.ok(await passwords.verify(seed.pass, demoPassword));
    const fields = await application.database.exclusive(db => db.all('PRAGMA table_info(payments)'));
    assert.ok(fields.every(field => !/card|password/i.test(field.name)));
    return { independentSalts: true, correctPasswordAccepted: true, incorrectPasswordRejected: true, seedHashed: true };
  });
  for (const table of ['payments', 'audit_logs']) {
    await scenario(`ROLLBACK-${table === 'payments' ? '01' : '02'}`, `Falha em ${table} reverte checkout inteiro e permite recuperação`, async () => {
      const triggerName = `validation_fail_${table}`;
      await application.database.exclusive(db => db.run(`CREATE TEMP TRIGGER ${triggerName} BEFORE INSERT ON ${table} BEGIN SELECT RAISE(ABORT, 'controlled-private-database-detail'); END`));
      try {
        const result = await unchanged(application, () => request(application, 'POST', '/api/checkout', {
          payload: checkout({ eml: `rollback-${table}@example.test` }),
        }));
        assert.equal(result.status, 500);
        assert.ok(!result.text.includes('controlled-private-database-detail'));
        assert.ok(!/SQLITE|INSERT|audit_logs|payments/.test(result.text));
      } finally {
        await application.database.exclusive(db => db.run(`DROP TRIGGER ${triggerName}`));
      }
      const recovery = await request(application, 'POST', '/api/checkout', {
        payload: checkout({ eml: `recovery-${table}@example.test` }),
      });
      assert.equal(recovery.status, 200);
      return { failedRequestStatus: 500, allStoredFieldsUnchangedAfterFailure: true, recoveryStatus: 200 };
    });
  }
  await scenario('ERROR-01', 'Falha em leitura financeira retorna 500 sanitizado', async () => {
    await application.database.exclusive(db => db.run('ALTER TABLE courses RENAME TO validation_hidden_courses'));
    try {
      const result = await request(application, 'GET', '/api/admin/financial-report', { authorized: true });
      assert.equal(result.status, 500);
      assert.ok(!/SQLITE|courses|SELECT|no such table/.test(result.text));
    } finally {
      await application.database.exclusive(db => db.run('ALTER TABLE validation_hidden_courses RENAME TO courses'));
    }
    const recovery = await request(application, 'GET', '/api/admin/financial-report', { authorized: true });
    assert.equal(recovery.status, 200);
    return { failedRequestStatus: 500, recoveryStatus: 200 };
  });
  await scenario('CONCURRENCY-01', 'Checkouts concorrentes reutilizam uma conta sem duplicação', async () => {
    const email = 'concurrent-checkout@example.test';
    const before = counts(await snapshot(application.database));
    const results = await Promise.all([1, 2].map(courseId => request(application, 'POST', '/api/checkout', {
      payload: checkout({ eml: email, c_id: courseId }),
    })));
    assert.deepEqual(results.map(result => result.status), [200, 200]);
    const after = await snapshot(application.database);
    assert.equal(after.users.filter(user => user.email === email).length, 1);
    assert.equal(after.users.length, before.users + 1);
    for (const table of ['enrollments', 'payments', 'audit_logs']) assert.equal(after[table].length, before[table] + 2);
    return { statuses: [200, 200], createdUsers: 1, createdEnrollments: 2 };
  });
  await scenario('CONCURRENCY-02', 'Leituras aguardam transação e não observam estado revertido', async () => {
    let enter;
    let release;
    const entered = new Promise(resolve => { enter = resolve; });
    const gate = new Promise(resolve => { release = resolve; });
    const before = await snapshot(application.database);
    const transaction = application.database.transaction(async db => {
      await db.run('INSERT INTO courses(title, price, active) VALUES (?, ?, ?)', ['Uncommitted hidden fixture', 999, 1]);
      enter();
      await gate;
      throw new Error('Expected rollback from isolation test');
    }).then(() => false, () => true);
    await entered;
    let readSettled = false;
    const queuedRead = application.database.exclusive(db => db.all('SELECT title FROM courses'))
      .then(rows => { readSettled = true; return rows; });
    const httpRead = request(application, 'GET', '/api/admin/financial-report', { authorized: true });
    let blocked;
    try {
      await new Promise(resolve => setTimeout(resolve, 40));
      blocked = !readSettled;
    } finally {
      release();
    }
    assert.ok(await transaction);
    const [rows, result] = await Promise.all([queuedRead, httpRead]);
    assert.ok(blocked);
    assert.ok(rows.every(row => row.title !== 'Uncommitted hidden fixture'));
    assert.equal(result.status, 200);
    assert.ok(result.body.every(course => course.course !== 'Uncommitted hidden fixture'));
    assert.deepEqual(await snapshot(application.database), before);
    return { readBlockedUntilRollback: true, dirtyRowsObserved: 0, httpStatus: result.status };
  });
  await scenario('REPORT-01', 'Relatório executa uma consulta com volume pequeno e grande', async () => {
    async function measuredReport() {
      return application.database.exclusive(async db => {
        let queryCount = 0;
        const measured = Object.fromEntries(['all', 'get', 'run'].map(method => [method, (...args) => {
          queryCount += 1;
          return db[method](...args);
        }]));
        const report = await reports.financial(measured);
        return { queryCount, report };
      });
    }
    const small = await measuredReport();
    assert.equal(small.queryCount, 1);
    const hash = await passwords.hash(password);
    const beforeRevenue = revenue(small.report);
    await application.database.transaction(async db => {
      const user = await db.run('INSERT INTO users(name,email,pass) VALUES (?,?,?)', ['Batch fixture', 'batch@example.test', hash]);
      for (let index = 0; index < 25; index += 1) {
        const course = await db.run('INSERT INTO courses(title,price,active) VALUES (?,?,1)', [`Batch course ${index}`, 10]);
        const enrollment = await db.run('INSERT INTO enrollments(user_id,course_id) VALUES (?,?)', [user.lastID, course.lastID]);
        await db.run('INSERT INTO payments(enrollment_id,amount,status) VALUES (?,?,?)', [enrollment.lastID, 10, index % 2 === 0 ? 'PAID' : 'DENIED']);
      }
    });
    const large = await measuredReport();
    assert.equal(large.queryCount, 1);
    assert.equal(large.report.length, small.report.length + 25);
    assert.equal(revenue(large.report), beforeRevenue + 130);
    assertReportShape(large.report);
    const result = await request(application, 'GET', '/api/admin/financial-report', { authorized: true });
    assert.equal(result.status, 200);
    assert.deepEqual(result.body, large.report);
    evidence.measurements.reportQueries = { small: small.queryCount, large: large.queryCount, addedCourses: 25 };
    return evidence.measurements.reportQueries;
  });
  await scenario('INTEGRITY-01', 'Chaves estrangeiras bloqueiam referências inexistentes', async () => {
    const before = await snapshot(application.database);
    await assert.rejects(application.database.transaction(db => db.run('INSERT INTO enrollments(user_id,course_id) VALUES (?,?)', [999999, 1])));
    assert.deepEqual(await snapshot(application.database), before);
    const violations = await application.database.exclusive(db => db.all('PRAGMA foreign_key_check'));
    assert.deepEqual(violations, []);
    return { invalidReferenceRejected: true, foreignKeyViolations: 0, allStoredFieldsUnchanged: true };
  });
  await scenario('OUTPUT-01', 'Respostas públicas e logs não contêm credenciais ou dados de pagamento', async () => {
    const result = await request(application, 'GET', '/api/admin/financial-report', { authorized: true });
    assertReportShape(result.body);
    const state = await snapshot(application.database);
    const output = JSON.stringify({ logs, response: result.body });
    for (const sensitive of [adminToken, password, wrongPassword, demoPassword, card, deniedCard, ...state.users.map(user => user.pass)]) {
      assert.ok(!output.includes(sensitive));
    }
    assert.ok(!/controlled-private-database-detail|Processando cartão|paymentGatewayKey/.test(output));
    assert.ok(logs.some(entry => entry.level === 'error'));
    return { sensitiveMarkersFound: 0, sanitizedErrorDiagnosticsPresent: true };
  });
}

async function noConfiguredToken() {
  await scenario('AUTH-04', 'Sem token configurado as rotas administrativas permanecem bloqueadas', async () => {
    const application = await startApplication({ host: '127.0.0.1', port: 0, adminToken: undefined, seedDemo: false });
    try {
      for (const token of [undefined, adminToken]) {
        for (const [method, route] of [['GET', '/api/admin/financial-report'], ['DELETE', '/api/users/1']]) {
          const result = await request(application, method, route, { token });
          assert.equal(result.status, 401);
        }
      }
      const empty = await snapshot(application.database);
      assert.ok(tableNames.every(table => empty[table].length === 0));
      return { rejectedCases: 4, status: 401, defaultBootUnseeded: true };
    } finally {
      await application.shutdown();
    }
  });
}

async function main() {
  sourceHashes(path.join(projectRoot, 'src'));
  let application;
  try {
    application = await startApplication({ host: '127.0.0.1', port: 0, adminToken, seedDemo: true, demoPassword });
    await baseline(application);
    await extended(application);
    await noConfiguredToken();
    evidence.boot = 'passed: current application factory, real loopback HTTP';
    evidence.operationCoverage = { exercised: 3, inventoried: 3 };
  } catch (error) {
    evidence.failure = error.message.startsWith('Validation stopped at ') ? error.message : 'Boot or validation infrastructure failed';
    process.exitCode = 1;
  } finally {
    if (application) {
      try {
        await application.shutdown();
      } catch {
        evidence.shutdown = 'failed';
        process.exitCode = 1;
      }
    }
    evidence.summary = {
      total: evidence.scenarios.length,
      passed: evidence.scenarios.filter(result => result.passed).length,
      failed: evidence.scenarios.filter(result => !result.passed).length,
    };
    const output = JSON.stringify(evidence, null, 2) + '\n';
    const jsonFlag = process.argv.indexOf('--json');
    if (jsonFlag !== -1) {
      const filename = process.argv[jsonFlag + 1];
      if (!filename) throw new Error('--json requires an output path');
      fs.writeFileSync(path.resolve(filename), output);
    }
    process.stdout.write(output);
  }
}

main().catch(() => {
  process.stderr.write('Validation infrastructure failed; no sensitive diagnostics were exported.\n');
  process.exitCode = 1;
});
