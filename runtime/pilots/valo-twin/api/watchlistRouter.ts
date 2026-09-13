import { z } from "zod";
import { createRouter, publicQuery } from "./middleware";
import { listWatchlist, addWatchlistEntry, updateWatchlistFlag } from "./queries/draftQueries";

export const watchlistRouter = createRouter({
  list: publicQuery.query(async () => {
    return listWatchlist();
  }),

  add: publicQuery
    .input(z.object({
      name: z.string().min(1),
      company: z.string().optional(),
      linkedinUrl: z.string().optional(),
      flag: z.enum(["monitor", "engage", "avoid", "critical"]).default("monitor"),
      notes: z.string().optional(),
    }))
    .mutation(async ({ input }) => {
      return addWatchlistEntry(input);
    }),

  updateFlag: publicQuery
    .input(z.object({
      id: z.number(),
      flag: z.enum(["monitor", "engage", "avoid", "critical"]),
    }))
    .mutation(async ({ input }) => {
      return updateWatchlistFlag(input.id, input.flag);
    }),
});
