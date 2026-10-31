const express = require('express');
const { timingSafeEqual } = require('node:crypto');
const { ApplicationError } = require('../errors');

const asyncRoute = handler => (req, res, next) =>
    Promise.resolve().then(() => handler(req, res, next)).catch(next);

function requireAdmin(adminToken) {
    const expected = adminToken ? Buffer.from(adminToken, 'utf8') : undefined;
    return (req, res, next) => {
        const authorization = req.get('authorization');
        const match = typeof authorization === 'string' && /^Bearer ([^\s]+)$/i.exec(authorization);
        const candidate = match ? Buffer.from(match[1], 'utf8') : undefined;
        if (!expected || !candidate || candidate.length !== expected.length ||
            !timingSafeEqual(candidate, expected)) {
            res.set('WWW-Authenticate', 'Bearer realm="administration"');
            return next(new ApplicationError(401, 'Não autorizado'));
        }
        return next();
    };
}

function createRoutes(controllers, { adminToken } = {}) {
    const router = express.Router();
    const authenticateAdmin = requireAdmin(adminToken);

    router.post('/api/checkout', asyncRoute(async (req, res) => {
        const result = await controllers.checkout(req.body);
        res.status(200).json({ msg: 'Sucesso', enrollment_id: result.enrollment_id });
    }));

    router.get('/api/admin/financial-report', authenticateAdmin, asyncRoute(async (req, res) => {
        const report = await controllers.financialReport();
        res.json(report.map(course => ({
            course: course.course,
            revenue: course.revenue,
            students: course.students.map(student => ({ student: student.student, paid: student.paid })),
        })));
    }));

    router.delete('/api/users/:id', authenticateAdmin, asyncRoute(async (req, res) => {
        const message = await controllers.deleteUser(req.params.id);
        res.status(200).type('text/plain').send(message);
    }));

    return router;
}

module.exports = { createRoutes };
