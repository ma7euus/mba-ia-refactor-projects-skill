async function financial(db) {
    const rows = await db.all(`
        SELECT c.id AS course_id, c.title, e.id AS enrollment_id,
               u.name AS student, p.amount, p.status
        FROM courses c
        LEFT JOIN enrollments e ON e.course_id = c.id
        LEFT JOIN users u ON u.id = e.user_id
        LEFT JOIN payments p ON p.enrollment_id = e.id
        ORDER BY c.id, e.id
    `);
    const courses = new Map();
    for (const row of rows) {
        if (!courses.has(row.course_id)) {
            courses.set(row.course_id, { course: row.title, revenue: 0, students: [] });
        }
        const course = courses.get(row.course_id);
        if (row.enrollment_id !== null) {
            course.students.push({ student: row.student ?? 'Unknown', paid: row.amount ?? 0 });
            if (row.status === 'PAID') course.revenue += row.amount;
        }
    }
    return [...courses.values()];
}

module.exports = { financial };
