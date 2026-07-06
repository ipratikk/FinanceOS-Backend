import { test } from 'node:test';
import assert from 'node:assert';
import { decryptPassword } from './passwordCrypto';

test('decrypts a known-good sealed password fixture', () => {
  process.env.IMPORT_PASSWORD_PRIVATE_KEY = 'jPD9lscFMxuYXKPA8rreVUQ1yCvF7I9cLXKJpvgHCqs=';
  const plaintext = decryptPassword({
    ephemeralPublicKey:
      'BMlpafZf5mr/ADpUNi81yut5ORTw8FZdJsm38X0+AXvNjAzkhzT4frPsmDHn1/fh88NuKrtqo+z3sYaJk5qy7g4=',
    ciphertext: 'AAAAAAAAAAAAAAAAbUGpYRAL7SenoVLK7IwGK3ZF5LOvH21l',
  });
  assert.strictEqual(plaintext, 'Test1234');
});

test('throws when IMPORT_PASSWORD_PRIVATE_KEY is not set', () => {
  delete process.env.IMPORT_PASSWORD_PRIVATE_KEY;
  assert.throws(() =>
    decryptPassword({ ephemeralPublicKey: 'AA==', ciphertext: 'AA==' }),
  );
});
