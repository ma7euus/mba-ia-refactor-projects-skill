const { randomBytes, scrypt, timingSafeEqual } = require('node:crypto');
const { promisify } = require('node:util');

const deriveKey = promisify(scrypt);
const parameters = Object.freeze({ N: 16384, r: 8, p: 1, maxmem: 64 * 1024 * 1024 });
const keyLength = 64;
const encoding = /^scrypt\$v1\$16384\$8\$1\$([a-f0-9]{32})\$([a-f0-9]{128})$/;

function validPassword(password) {
    return typeof password === 'string' && password.length > 0 && Buffer.byteLength(password, 'utf8') <= 1024;
}

async function hash(password) {
    if (!validPassword(password)) throw new TypeError('Invalid password');
    const salt = randomBytes(16);
    const key = await deriveKey(password, salt, keyLength, parameters);
    return `scrypt$v1$16384$8$1$${salt.toString('hex')}$${key.toString('hex')}`;
}

async function verify(stored, candidate) {
    if (typeof stored !== 'string' || !validPassword(candidate)) return false;
    const match = encoding.exec(stored);
    if (!match) return false;
    const key = await deriveKey(candidate, Buffer.from(match[1], 'hex'), keyLength, parameters);
    return timingSafeEqual(key, Buffer.from(match[2], 'hex'));
}

module.exports = { hash, verify };
