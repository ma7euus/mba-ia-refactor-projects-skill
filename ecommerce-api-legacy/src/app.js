const express = require('express');
const { loadConfig } = require('./config');
const { createDatabase } = require('./database');
const { seedDemo } = require('./seed');
const { createCheckout } = require('./services/checkout');
const { createControllers } = require('./controllers');
const { createRoutes } = require('./views/routes');
const { errorHandler } = require('./errors');

async function createApplication({ config = loadConfig(), logger = console } = {}) {
    const database = await createDatabase();
    try {
        if (config.seedDemo) await seedDemo(database, config.demoPassword);
        const app = express();
        app.disable('x-powered-by');
        app.use(express.json({ limit: '16kb' }));
        const checkout = createCheckout({ database });
        const controllers = createControllers({ database, checkout });
        app.use(createRoutes(controllers, { adminToken: config.adminToken }));
        app.use(errorHandler(logger));
        return { app, database, close: () => database.close() };
    } catch (error) {
        await database.close();
        throw error;
    }
}

async function start() {
    const config = loadConfig();
    const application = await createApplication({ config });
    const server = application.app.listen(config.port, config.host);
    await new Promise((resolve, reject) => {
        server.once('listening', resolve);
        server.once('error', reject);
    }).catch(async error => {
        await application.close();
        throw error;
    });
    console.log(`LMS pronto em http://${config.host}:${server.address().port}`);
    let stopping = false;
    const shutdown = async () => {
        if (stopping) return;
        stopping = true;
        try {
            await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
            await application.close();
        } catch {
            console.error('shutdown_failed');
            process.exitCode = 1;
        }
    };
    process.once('SIGINT', shutdown);
    process.once('SIGTERM', shutdown);
    return { server, ...application };
}

if (require.main === module) {
    start().catch(() => {
        console.error('startup_failed: confira configuração, porta e dependências');
        process.exitCode = 1;
    });
}

module.exports = { createApplication, start };
