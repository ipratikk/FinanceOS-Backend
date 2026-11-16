import { test } from 'node:test';
import assert from 'node:assert';

test('uploadStatement records a StatementImport row after a successful import', async (t) => {
  const created: unknown[] = [];
  const prismaMock = {
    statementImport: { create: async (args: unknown) => { created.push(args); return args; } },
    ledger: {
      findUniqueOrThrow: async () => ({ id: 'ledger-1', displayName: 'HDFC', bank: {} }),
    },
  };
  const pythonService = {
    parseFile: async () => ({
      bank_code: 'hdfc', count: 1, last4: '1234', password_required: false,
      transactions: [{ postedAt: '2026-06-01', description: 'x', amountMinorUnits: -100,
        currencyCode: 'INR', sourceFingerprint: 'fp' }],
    }),
    importTransactions: async () => ({ imported: 1, duplicates: 2, errors: [] }),
  };

  t.mock.module('../services/python.ts', { namedExports: pythonService });
  t.mock.module('../prisma/client.ts', { defaultExport: prismaMock });
  const { uploadResolvers } = await import('./upload');

  const file = Promise.resolve({
    filename: 'stmt.csv', mimetype: 'text/csv', encoding: '7bit',
    createReadStream: () => {
      const { Readable } = require('stream');
      return Readable.from([Buffer.from('a,b')]);
    },
  });
  await uploadResolvers.Mutation.uploadStatement(null, { ledgerId: 'ledger-1', file });

  assert.deepStrictEqual(created, [{
    data: { ledgerId: 'ledger-1', imported: 1, duplicates: 2, closingBalance: null, closingBalanceAsOf: null },
  }]);
});
