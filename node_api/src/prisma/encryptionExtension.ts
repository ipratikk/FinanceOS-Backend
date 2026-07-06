import { Prisma } from '@prisma/client';
import { encrypt, decrypt } from '../services/columnCrypto';

export const encryptOnWrite = Prisma.defineExtension({
  query: {
    ledger: {
      create({ args, query }) {
        if (typeof args.data.last4 === 'string') {
          args.data.last4 = encrypt(args.data.last4) as string;
        }
        return query(args);
      },
      update({ args, query }) {
        if (typeof args.data.last4 === 'string') {
          args.data.last4 = encrypt(args.data.last4) as string;
        }
        return query(args);
      },
    },
  },
});

export const decryptOnRead = Prisma.defineExtension({
  result: {
    ledger: {
      last4: {
        needs: { last4: true },
        compute(ledger) {
          return decrypt(ledger.last4);
        },
      },
    },
    transaction: {
      narration: {
        needs: { narration: true },
        compute(transaction) {
          return decrypt(transaction.narration) ?? transaction.narration;
        },
      },
      merchant: {
        needs: { merchant: true },
        compute(transaction) {
          return decrypt(transaction.merchant);
        },
      },
    },
  },
});
