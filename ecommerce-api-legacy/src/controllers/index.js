const users = require('../models/users');
const reports = require('../models/reports');
const { ApplicationError } = require('../errors');

function readUserId(rawId) {
    if (typeof rawId !== 'string' || !/^[1-9]\d*$/.test(rawId)) {
        throw new ApplicationError(400, 'Bad Request');
    }
    const userId = Number(rawId);
    if (!Number.isSafeInteger(userId)) {
        throw new ApplicationError(400, 'Bad Request');
    }
    return userId;
}

function createControllers({ database, checkout }) {
    return {
        checkout(payload) {
            return checkout.execute(payload);
        },

        financialReport() {
            return database.exclusive(db => reports.financial(db));
        },

        async deleteUser(rawId) {
            const userId = readUserId(rawId);
            return database.transaction(async db => {
                if (!await users.findById(db, userId)) {
                    throw new ApplicationError(404, 'Usuário não encontrado');
                }
                if (await users.hasEnrollments(db, userId)) {
                    throw new ApplicationError(409, 'Usuário possui matrículas');
                }
                const removed = await users.remove(db, userId);
                if (removed !== 1) throw new Error('Deletion did not remove the selected user');
                return 'Usuário deletado';
            });
        },
    };
}

module.exports = { createControllers };
