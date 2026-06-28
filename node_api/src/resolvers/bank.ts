import prisma from '../prisma/client';

export const bankResolvers = {
  Query: {
    banks: () => prisma.bank.findMany(),
  },
  Mutation: {
    createBank: (_: unknown, { input }: { input: { name: string; code: string } }) =>
      prisma.bank.create({ data: { name: input.name, code: input.code.toUpperCase() } }),
    clearAllData: async () => {
      await prisma.transaction.deleteMany();
      await prisma.ledger.deleteMany();
      await prisma.bank.deleteMany();
      return true;
    },
  },
  Bank: {
    ledgers: (parent: { id: string }) =>
      prisma.ledger.findMany({ where: { bankId: parent.id } }),
  },
};
