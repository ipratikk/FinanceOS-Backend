import prisma from '../prisma/client';

export const ledgerResolvers = {
  Query: {
    ledgers: () => prisma.ledger.findMany({ include: { bank: true } }),
    ledger: (_: unknown, { id }: { id: string }) =>
      prisma.ledger.findUnique({ where: { id }, include: { bank: true } }),
  },
  Mutation: {
    createLedger: (
      _: unknown,
      { input }: { input: { displayName: string; kind: string; last4?: string; bankId: string } },
    ) => prisma.ledger.create({ data: input as any, include: { bank: true } }),
    updateLedger: (
      _: unknown,
      { id, input }: { id: string; input: Partial<{ displayName: string; kind: string; last4: string }> },
    ) => prisma.ledger.update({ where: { id }, data: input as any, include: { bank: true } }),
    deleteLedger: async (_: unknown, { id }: { id: string }) => {
      await prisma.ledger.delete({ where: { id } });
      return true;
    },
  },
  Ledger: {
    bank: (parent: { bankId: string }) =>
      prisma.bank.findUnique({ where: { id: parent.bankId } }),
    transactions: (
      parent: { id: string },
      { filter }: { filter?: { from?: string; to?: string; category?: string; minAmount?: number; maxAmount?: number } },
    ) => {
      const where: Record<string, unknown> = { ledgerId: parent.id };
      if (filter?.from) where.date = { gte: new Date(filter.from) };
      if (filter?.to) where.date = { ...(where.date as object ?? {}), lte: new Date(filter.to) };
      if (filter?.category) where.category = filter.category;
      if (filter?.minAmount != null) where.amountMinorUnits = { gte: filter.minAmount };
      if (filter?.maxAmount != null) where.amountMinorUnits = { ...(where.amountMinorUnits as object ?? {}), lte: filter.maxAmount };
      return prisma.transaction.findMany({ where, orderBy: { date: 'desc' } });
    },
    balance: async (parent: { id: string }) => {
      const result = await prisma.transaction.aggregate({
        where: { ledgerId: parent.id },
        _sum: { amountMinorUnits: true },
      });
      return { value: result._sum.amountMinorUnits ?? 0, currencyCode: 'INR' };
    },
  },
};
