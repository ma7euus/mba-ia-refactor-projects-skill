async function createCheckout(db, { courseId, userId }) {
    const result = await db.run('INSERT INTO audit_logs (action) VALUES (?)',
        [`Checkout curso ${courseId} por ${userId}`]);
    return result.lastID;
}

module.exports = { createCheckout };
