import { getAnalytics } from '../services/python';

export const analyticsResolvers = {
  Query: {
    analytics: async (
      _: unknown,
      { ledgerId, from, to }: { ledgerId?: string; from?: string; to?: string },
    ) => {
      const data = await getAnalytics(ledgerId, from, to) as any;
      return data;
    },
  },
};
