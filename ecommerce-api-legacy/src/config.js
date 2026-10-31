function loadConfig(env = process.env) {
    const host = env.HOST === undefined ? '127.0.0.1' : env.HOST;
    const rawPort = env.PORT === undefined ? '3000' : env.PORT;
    if (typeof host !== 'string' || !host.trim() || host.length > 255) {
        throw new Error('HOST deve indicar um endereço válido');
    }
    if (typeof rawPort !== 'string' || !/^\d+$/.test(rawPort)) {
        throw new Error('PORT deve ser um inteiro entre 0 e 65535');
    }
    const port = Number(rawPort);
    if (!Number.isSafeInteger(port) || port > 65535) {
        throw new Error('PORT deve ser um inteiro entre 0 e 65535');
    }

    const seedFlag = env.SEED_DEMO_DATA;
    if (seedFlag !== undefined && seedFlag !== '0' && seedFlag !== '1') {
        throw new Error('SEED_DEMO_DATA deve ser 0 ou 1');
    }
    const seedDemo = seedFlag === '1';
    const demoPassword = env.DEMO_USER_PASSWORD;
    if (seedDemo && (typeof demoPassword !== 'string' || !demoPassword.trim().length ||
        Buffer.byteLength(demoPassword, 'utf8') > 1024)) {
        throw new Error('DEMO_USER_PASSWORD é obrigatória para o seed e deve ter até 1024 bytes');
    }

    const adminToken = env.ADMIN_API_TOKEN || undefined;
    if (adminToken !== undefined && (typeof adminToken !== 'string' ||
        adminToken.length < 32 || adminToken.length > 1024 || /\s/.test(adminToken))) {
        throw new Error('ADMIN_API_TOKEN deve ter de 32 a 1024 caracteres sem espaços; gere um valor aleatório');
    }

    return Object.freeze({ host, port, adminToken, seedDemo, demoPassword });
}

module.exports = { loadConfig };
