import prisma from '../prisma/client';

export const bankResolvers = {
  Query: {
    banks: () => prisma.bank.findMany(),
  },
  Bank: {
    ledgers: (parent: { id: string }) =>
      prisma.ledger.findMany({ where: { bankId: parent.id } }),
  },
};
