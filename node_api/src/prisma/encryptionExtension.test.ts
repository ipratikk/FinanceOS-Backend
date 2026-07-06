import { test } from 'node:test';
import assert from 'node:assert';
import { PrismaClient } from '@prisma/client';
import prisma from './client';

const rawClient = new PrismaClient();

test('last4 is encrypted at rest and decrypted on read', async () => {
  const bank = await rawClient.bank.create({
    data: { name: 'Encryption Test Bank', code: `ENCTEST${Date.now()}` },
  });

  const ledger = await prisma.ledger.create({
    data: { displayName: 'Encryption Test Ledger', kind: 'BANK_ACCOUNT', last4: '4242', bankId: bank.id },
  });

  // The critical assertion: read the RAW row via the unextended client.
  // If this is plaintext '4242', encryption isn't happening.
  const raw = await rawClient.ledger.findUnique({ where: { id: ledger.id } });
  assert.notStrictEqual(raw?.last4, '4242');

  // Read via the extended client — should transparently decrypt back to '4242'.
  const decrypted = await prisma.ledger.findUnique({ where: { id: ledger.id } });
  assert.strictEqual(decrypted?.last4, '4242');

  // Nested include — the specific case a naive query-only extension would miss.
  const bankWithLedgers = await prisma.bank.findUnique({
    where: { id: bank.id },
    include: { ledgers: true },
  });
  assert.strictEqual(bankWithLedgers?.ledgers[0]?.last4, '4242');

  await rawClient.ledger.delete({ where: { id: ledger.id } });
  await rawClient.bank.delete({ where: { id: bank.id } });
});

test('null last4 round-trips as null', async () => {
  const bank = await rawClient.bank.create({
    data: { name: 'Encryption Test Bank 2', code: `ENCTEST2${Date.now()}` },
  });
  const ledger = await prisma.ledger.create({
    data: { displayName: 'No Last4 Ledger', kind: 'WALLET', bankId: bank.id },
  });
  const read = await prisma.ledger.findUnique({ where: { id: ledger.id } });
  assert.strictEqual(read?.last4, null);

  await rawClient.ledger.delete({ where: { id: ledger.id } });
  await rawClient.bank.delete({ where: { id: bank.id } });
});
