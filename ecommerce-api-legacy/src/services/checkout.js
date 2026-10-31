const { ApplicationError } = require('../errors');
const users = require('../models/users');
const courses = require('../models/courses');
const enrollments = require('../models/enrollments');
const payments = require('../models/payments');
const audit = require('../models/audit');
const passwords = require('./passwords');
const { simulatePayment, PAYMENT_PAID } = require('./payment');

function requiredText(value, maxLength) {
    return typeof value === 'string' && value.trim().length > 0 && value.length <= maxLength;
}

function readCheckout(payload) {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)
        || !requiredText(payload.usr, 200)
        || !requiredText(payload.eml, 254)
        || !requiredText(payload.pwd, 1024)
        || Buffer.byteLength(payload.pwd, 'utf8') > 1024
        || !requiredText(payload.card, 64)
        || !Number.isSafeInteger(payload.c_id) || payload.c_id < 1
        || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(payload.eml.trim())) {
        throw new ApplicationError(400, 'Bad Request');
    }
    return {
        userName: payload.usr.trim(), email: payload.eml.trim(), password: payload.pwd,
        courseId: payload.c_id, card: payload.card,
    };
}

function createCheckout({ database }) {
    return {
        async execute(payload) {
            const input = readCheckout(payload);
            // The queue owns the whole transaction, including asynchronous password work.
            return database.transaction(async db => {
                const course = await courses.findActiveById(db, input.courseId);
                if (!course) throw new ApplicationError(404, 'Curso não encontrado');

                const user = await users.findByEmail(db, input.email);
                if (user && !await passwords.verify(user.pass, input.password)) {
                    throw new ApplicationError(401, 'Credenciais inválidas');
                }
                const status = simulatePayment(input.card);
                if (status !== PAYMENT_PAID) throw new ApplicationError(400, 'Pagamento recusado');

                const userId = user ? user.id : await users.create(db, {
                    name: input.userName, email: input.email,
                    passwordHash: await passwords.hash(input.password),
                });
                const enrollmentId = await enrollments.create(db, { userId, courseId: course.id });
                await payments.create(db, { enrollmentId, amount: course.price, status });
                await audit.createCheckout(db, { courseId: course.id, userId });
                return { enrollment_id: enrollmentId };
            });
        },
    };
}

module.exports = { createCheckout };
