import prisma from '../prisma/client';

export const transactionResolvers = {
  Query: {
    transactions: (
      _: unknown,
      { ledgerId, filter }: { ledgerId?: string; filter?: { from?: string; to?: string; category?: string } },
    ) => {
      const where: Record<string, unknown> = {};
      if (ledgerId) where.ledgerId = ledgerId;
      if (filter?.from) where.date = { gte: new Date(filter.from) };
      if (filter?.to) where.date = { ...(where.date as object ?? {}), lte: new Date(filter.to) };
      if (filter?.category) where.category = filter.category;
      return prisma.transaction.findMany({ where, orderBy: { date: 'desc' } });
    },
  },
  Mutation: {
    recategorize: (_: unknown, { transactionId, category }: { transactionId: string; category: string }) =>
      prisma.transaction.update({
        where: { id: transactionId },
        data: { category },
        include: { ledger: true },
      }),
  },
  Transaction: {
    date: (parent: { date: Date | string }) =>
      parent.date instanceof Date ? parent.date.toISOString() : parent.date,
    ledger: (parent: { ledgerId: string }) =>
      prisma.ledger.findUnique({ where: { id: parent.ledgerId }, include: { bank: true } }),
  },
};
