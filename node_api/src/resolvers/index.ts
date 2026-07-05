import { GraphQLUpload } from 'graphql-upload-ts';
import { bankResolvers } from './bank';
import { ledgerResolvers } from './ledger';
import { transactionResolvers } from './transaction';
import { uploadResolvers } from './upload';
import { previewResolvers } from './preview';
import { analyticsResolvers } from './analytics';

export const resolvers = {
  Upload: GraphQLUpload,
  Query: {
    health: () => 'ok',
    ...bankResolvers.Query,
    ...ledgerResolvers.Query,
    ...transactionResolvers.Query,
    ...analyticsResolvers.Query,
  },
  Mutation: {
    ...bankResolvers.Mutation,
    ...ledgerResolvers.Mutation,
    ...transactionResolvers.Mutation,
    ...uploadResolvers.Mutation,
    ...previewResolvers.Mutation,
  },
  Bank: bankResolvers.Bank,
  Ledger: ledgerResolvers.Ledger,
  Transaction: transactionResolvers.Transaction,
};
