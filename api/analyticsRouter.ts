import { z } from "zod";
import { createRouter, publicQuery } from "./middleware";
import { getStats, getRecentActivity } from "./queries/draftQueries";

export const analyticsRouter = createRouter({
  stats: publicQuery.query(async () => {
    return getStats();
  }),

  activity: publicQuery
    .input(z.object({ limit: z.number().min(1).max(100).default(20) }).optional())
    .query(async ({ input }) => {
      return getRecentActivity(input?.limit || 20);
    }),
});
