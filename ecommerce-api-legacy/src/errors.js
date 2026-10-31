const APPLICATION_STATUSES = new Set([400, 401, 403, 404, 409]);

class ApplicationError extends Error {
    constructor(status, message) {
        super(message);
        if (!APPLICATION_STATUSES.has(status)) {
            throw new TypeError('Status de aplicação inválido');
        }
        this.name = 'ApplicationError';
        this.status = status;
    }
}

function errorHandler(logger = console) {
    return (error, req, res, next) => {
        if (res.headersSent) return next(error);
        if (error instanceof ApplicationError) {
            return res.status(error.status).type('text/plain').send(error.message);
        }
        if (error.type === 'entity.parse.failed' && error.status === 400) {
            return res.status(400).type('text/plain').send('Bad Request');
        }
        if (error instanceof URIError && error.status === 400) {
            return res.status(400).type('text/plain').send('Bad Request');
        }
        if (error.type === 'entity.too.large' && error.status === 413) {
            return res.status(413).type('text/plain').send('Payload muito grande');
        }
        if (['charset.unsupported', 'encoding.unsupported'].includes(error.type) && error.status === 415) {
            return res.status(415).type('text/plain').send('Formato não suportado');
        }
        // Do not log exception messages, SQL, request bodies or credentials.
        logger.error('request_failed');
        return res.status(500).type('text/plain').send('Erro interno');
    };
}

module.exports = { ApplicationError, errorHandler };
