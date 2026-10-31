const passwords = require('./services/passwords');
const users = require('./models/users');
const enrollments = require('./models/enrollments');
const payments = require('./models/payments');

async function seedDemo(database, password) {
    const passwordHash = await passwords.hash(password);
    await database.transaction(async db => {
        const existing = await db.get(`SELECT
            (SELECT COUNT(*) FROM courses) + (SELECT COUNT(*) FROM users) +
            (SELECT COUNT(*) FROM enrollments) + (SELECT COUNT(*) FROM payments) +
            (SELECT COUNT(*) FROM audit_logs) AS total`);
        if (existing.total !== 0) throw new Error('Demo seed requires an empty database');
        await db.run('INSERT INTO courses (title, price, active) VALUES (?, ?, ?), (?, ?, ?)',
            ['Clean Architecture', 997, 1, 'Docker', 497, 1]);
        const userId = await users.create(db, {
            name: 'Leonan', email: 'leonan@fullcycle.com.br', passwordHash,
        });
        const enrollmentId = await enrollments.create(db, { userId, courseId: 1 });
        await payments.create(db, { enrollmentId, amount: 997, status: 'PAID' });
    });
}

module.exports = { seedDemo };
