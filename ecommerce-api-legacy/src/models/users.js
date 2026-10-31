function findByEmail(db, email) {
    return db.get('SELECT id, name, email, pass FROM users WHERE email = ?', [email]);
}

function findById(db, userId) {
    return db.get('SELECT id, name, email FROM users WHERE id = ?', [userId]);
}

async function create(db, { name, email, passwordHash }) {
    const result = await db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
        [name, email, passwordHash]);
    return result.lastID;
}

async function remove(db, userId) {
    const result = await db.run('DELETE FROM users WHERE id = ?', [userId]);
    return result.changes;
}

async function hasEnrollments(db, userId) {
    return Boolean(await db.get('SELECT 1 FROM enrollments WHERE user_id = ? LIMIT 1', [userId]));
}

module.exports = { findByEmail, findById, create, remove, hasEnrollments };
