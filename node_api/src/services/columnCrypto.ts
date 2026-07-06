import crypto from 'crypto';

const KEY_ENV_VAR = 'DATABASE_ENCRYPTION_KEY';

function loadKey(): Buffer {
  const raw = process.env[KEY_ENV_VAR];
  if (!raw) {
    throw new Error(`${KEY_ENV_VAR} is not set`);
  }
  const key = Buffer.from(raw, 'base64');
  if (key.length !== 32) {
    throw new Error(`${KEY_ENV_VAR} must decode to exactly 32 bytes, got ${key.length}`);
  }
  return key;
}

const KEY = loadKey();

export function encrypt(plaintext: string | null): string | null {
  if (plaintext === null) return null;
  const nonce = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', KEY, nonce);
  const ciphertext = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  const tag = cipher.getAuthTag();
  const combined = Buffer.concat([nonce, ciphertext, tag]);
  return combined.toString('base64');
}

export function decrypt(ciphertext: string | null): string | null {
  if (ciphertext === null) return null;
  const combined = Buffer.from(ciphertext, 'base64');
  const nonce = combined.subarray(0, 12);
  const tag = combined.subarray(combined.length - 16);
  const encrypted = combined.subarray(12, combined.length - 16);
  const decipher = crypto.createDecipheriv('aes-256-gcm', KEY, nonce);
  decipher.setAuthTag(tag);
  const plaintext = Buffer.concat([decipher.update(encrypted), decipher.final()]);
  return plaintext.toString('utf8');
}
