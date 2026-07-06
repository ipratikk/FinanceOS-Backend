import { test } from 'node:test';
import assert from 'node:assert';

const FIXTURE_KEY_B64 = 'U8tnbclQVVEUNzwLJnolbbWQMQuJsWT0zscl3Y9ppQI=';
const FIXTURE_COMBINED_B64 =
  'AAAAAAAAAAAAAAAATcnnQwD0zPLEOm1Lv34+K2YUzKOnO+tl8/Ej/WNNwRI=';
const FIXTURE_PLAINTEXT = 'SWIGGY BANGALORE';

process.env.DATABASE_ENCRYPTION_KEY = FIXTURE_KEY_B64;
import { encrypt, decrypt } from './columnCrypto';

test('encrypt/decrypt round trip', () => {
  const ciphertext = encrypt('some narration text');
  assert.notStrictEqual(ciphertext, 'some narration text');
  assert.strictEqual(decrypt(ciphertext), 'some narration text');
});

test('encrypt(null) passes through', () => {
  assert.strictEqual(encrypt(null), null);
});

test('decrypt(null) passes through', () => {
  assert.strictEqual(decrypt(null), null);
});

test('decrypts a fixture produced by Python\'s cryptography library', () => {
  // Cross-language interop: this exact ciphertext was generated in Python
  // (Task 1's fixture) and independently verified decryptable there too —
  // this test proves Node's decrypt() parses the same nonce||ct||tag wire
  // format identically.
  assert.strictEqual(decrypt(FIXTURE_COMBINED_B64), FIXTURE_PLAINTEXT);
});
