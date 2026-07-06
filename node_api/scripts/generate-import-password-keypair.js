const crypto = require('crypto');

const ecdh = crypto.createECDH('prime256v1');
ecdh.generateKeys();

console.log('IMPORT_PASSWORD_PRIVATE_KEY (put this in node_api/.env, never commit it):');
console.log(ecdh.getPrivateKey().toString('base64'));
console.log();
console.log('Public key (paste this into ImportPasswordCrypto.swift\'s backendPublicKey constant, Task 5):');
console.log(ecdh.getPublicKey().toString('base64'));
