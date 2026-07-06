import crypto from 'crypto';

const HKDF_INFO = Buffer.from('financeos-import-password-v1', 'utf8');

export interface EncryptedPassword {
  ephemeralPublicKey: string;
  ciphertext: string;
}

export function decryptPassword(encrypted: EncryptedPassword): string {
  const privateKeyB64 = process.env.IMPORT_PASSWORD_PRIVATE_KEY;
  if (!privateKeyB64) {
    throw new Error('IMPORT_PASSWORD_PRIVATE_KEY is not set');
  }
  const privateKey = Buffer.from(privateKeyB64, 'base64');
  const ephemeralPublicKey = Buffer.from(encrypted.ephemeralPublicKey, 'base64');
  const combined = Buffer.from(encrypted.ciphertext, 'base64');

  const ecdh = crypto.createECDH('prime256v1');
  ecdh.setPrivateKey(privateKey);
  const sharedSecret = ecdh.computeSecret(ephemeralPublicKey);

  const aesKey = Buffer.from(
    crypto.hkdfSync('sha256', sharedSecret, Buffer.alloc(0), HKDF_INFO, 32),
  );

  const nonce = combined.subarray(0, 12);
  const tag = combined.subarray(combined.length - 16);
  const ciphertext = combined.subarray(12, combined.length - 16);

  const decipher = crypto.createDecipheriv('aes-256-gcm', aesKey, nonce);
  decipher.setAuthTag(tag);
  const plaintext = Buffer.concat([decipher.update(ciphertext), decipher.final()]);
  return plaintext.toString('utf8');
}
