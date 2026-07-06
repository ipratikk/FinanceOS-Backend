import { test } from 'node:test';
import assert from 'node:assert';

test('uploadStatement throws when password_required comes back true', async (t) => {
  const pythonService = {
    parseFile: async () => ({
      bank_code: '',
      count: 0,
      last4: null,
      password_required: true,
      transactions: [],
    }),
    importTransactions: async () => {
      throw new Error('should not be called');
    },
  };
  const passwordCrypto = { decryptPassword: () => 'plaintext-password' };

  t.mock.module('../services/python.ts', { namedExports: pythonService });
  t.mock.module('../services/passwordCrypto.ts', { namedExports: passwordCrypto });
  const { uploadResolvers } = await import('./upload');

  const fakeFile = Promise.resolve({
    filename: 'test.pdf',
    mimetype: 'application/pdf',
    encoding: '7bit',
    createReadStream: () => {
      const { Readable } = require('stream');
      return Readable.from([Buffer.from('fake pdf bytes')]);
    },
  });

  await assert.rejects(
    uploadResolvers.Mutation.uploadStatement(null, {
      ledgerId: 'fake-id',
      file: fakeFile,
      password: { ephemeralPublicKey: 'AA==', ciphertext: 'AA==' },
    }),
  );
});
