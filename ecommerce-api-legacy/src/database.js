const sqlite3 = require('sqlite3');

const schema = [
    `CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 200),
        email TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK(length(email) BETWEEN 3 AND 254),
        pass TEXT NOT NULL CHECK(length(pass) > 0)
    )`,
    `CREATE TABLE courses (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL CHECK(length(trim(title)) > 0),
        price REAL NOT NULL CHECK(typeof(price) IN ('integer', 'real') AND price >= 0),
        active INTEGER NOT NULL CHECK(active IN (0, 1))
    )`,
    `CREATE TABLE enrollments (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE RESTRICT
    )`,
    `CREATE TABLE payments (
        id INTEGER PRIMARY KEY,
        enrollment_id INTEGER NOT NULL UNIQUE REFERENCES enrollments(id) ON DELETE RESTRICT,
        amount REAL NOT NULL CHECK(typeof(amount) IN ('integer', 'real') AND amount >= 0),
        status TEXT NOT NULL CHECK(status IN ('PAID', 'DENIED'))
    )`,
    `CREATE TABLE audit_logs (
        id INTEGER PRIMARY KEY,
        action TEXT NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )`,
    'CREATE INDEX enrollments_user_idx ON enrollments(user_id)',
    'CREATE INDEX enrollments_course_idx ON enrollments(course_id)',
];

async function createDatabase() {
    let connection;
    await new Promise((resolve, reject) => {
        connection = new sqlite3.Database(':memory:', error => error ? reject(error) : resolve());
    });

    const execute = (method, sql, params = []) => new Promise((resolve, reject) => {
        connection[method](sql, params, function complete(error, result) {
            if (error) return reject(error);
            return resolve(method === 'run' ? { lastID: this.lastID, changes: this.changes } : result);
        });
    });

    // Queue complete use cases, including their awaited work, instead of individual SQL calls.
    let queue = Promise.resolve();
    let closing = false;
    let closePromise;

    function enqueue(operation) {
        if (closing) return Promise.reject(new Error('Database is closing'));
        const result = queue.then(operation);
        queue = result.catch(() => {});
        return result;
    }

    async function scoped(operation) {
        let active = true;
        const invoke = (method, sql, params) => active
            ? execute(method, sql, params)
            : Promise.reject(new Error('Database scope has ended'));
        const scope = Object.freeze({
            run: (sql, params) => invoke('run', sql, params),
            get: (sql, params) => invoke('get', sql, params),
            all: (sql, params) => invoke('all', sql, params),
        });
        try {
            return await operation(scope);
        } finally {
            active = false;
        }
    }

    const database = {
        exclusive(operation) {
            return enqueue(() => scoped(operation));
        },
        transaction(operation) {
            return enqueue(async () => {
                await execute('run', 'BEGIN IMMEDIATE');
                try {
                    const result = await scoped(operation);
                    await execute('run', 'COMMIT');
                    return result;
                } catch (error) {
                    try {
                        await execute('run', 'ROLLBACK');
                    } catch (rollbackError) {
                        throw new AggregateError([error, rollbackError], 'Transaction rollback failed');
                    }
                    throw error;
                }
            });
        },
        close() {
            if (!closePromise) {
                closing = true;
                closePromise = queue.then(() => new Promise((resolve, reject) => {
                    connection.close(error => error ? reject(error) : resolve());
                }));
            }
            return closePromise;
        },
    };

    try {
        await database.exclusive(async db => {
            await db.run('PRAGMA foreign_keys = ON');
            for (const statement of schema) await db.run(statement);
        });
        return Object.freeze(database);
    } catch (error) {
        await database.close();
        throw error;
    }
}

module.exports = { createDatabase };
