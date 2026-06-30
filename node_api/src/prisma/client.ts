import { PrismaClient } from '@prisma/client';
import { randomBytes } from 'crypto';

const LEDGER_PREFIX: Record<string, string> = {
  BANK_ACCOUNT: 'AC',
  CREDIT_CARD: 'CC',
  LOAN: 'LN',
  WALLET: 'WL',
  CRYPTO: 'CR',
  INVESTMENT: 'INV',
};

function prefixedId(prefix: string): string {
  return `${prefix}-${randomBytes(4).toString('hex').toUpperCase()}`;
}

const prisma = new PrismaClient().$extends({
  query: {
    bank: {
      create({ args, query }) {
        if (!args.data.id) args.data.id = prefixedId('BA');
        return query(args);
      },
    },
    ledger: {
      create({ args, query }) {
        if (!args.data.id) {
          const kind = args.data.kind as string;
          args.data.id = prefixedId(LEDGER_PREFIX[kind] ?? 'LD');
        }
        return query(args);
      },
    },
  },
});

export default prisma;
