function findActiveById(db, courseId) {
    return db.get('SELECT id, title, price FROM courses WHERE id = ? AND active = 1', [courseId]);
}

module.exports = { findActiveById };
