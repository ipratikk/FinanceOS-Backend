import { test, mock } from 'node:test';
import assert from 'node:assert';

test('previewStatement maps password_required through', async (t) => {
  const pythonService = { parseFile: mock.fn(async () => ({
    bank_code: '',
    count: 0,
    last4: null,
    password_required: true,
    transactions: [],
  })) };
  const passwordCrypto = { decryptPassword: mock.fn(() => 'plaintext-password') };

  t.mock.module('../services/python.ts', { namedExports: pythonService });
  t.mock.module('../services/passwordCrypto.ts', { namedExports: passwordCrypto });
  const { previewResolvers } = await import('./preview');

  const fakeFile = Promise.resolve({
    filename: 'test.pdf',
    mimetype: 'application/pdf',
    encoding: '7bit',
    createReadStream: () => {
      const { Readable } = require('stream');
      return Readable.from([Buffer.from('fake pdf bytes')]);
    },
  });

  const result = await previewResolvers.Mutation.previewStatement(null, {
    file: fakeFile,
    password: { ephemeralPublicKey: 'AA==', ciphertext: 'AA==' },
  });

  assert.strictEqual(result.passwordRequired, true);
  assert.strictEqual(passwordCrypto.decryptPassword.mock.calls.length, 1);
});
