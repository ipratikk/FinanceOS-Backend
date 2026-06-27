import { bankResolvers } from './bank';
import { ledgerResolvers } from './ledger';
import { transactionResolvers } from './transaction';
import { uploadResolvers } from './upload';
import { analyticsResolvers } from './analytics';

export const resolvers = {
  Query: {
    health: () => 'ok',
    ...bankResolvers.Query,
    ...ledgerResolvers.Query,
    ...transactionResolvers.Query,
    ...analyticsResolvers.Query,
  },
  Mutation: {
    ...ledgerResolvers.Mutation,
    ...transactionResolvers.Mutation,
    ...uploadResolvers.Mutation,
  },
  Bank: bankResolvers.Bank,
  Ledger: ledgerResolvers.Ledger,
  Transaction: transactionResolvers.Transaction,
};
