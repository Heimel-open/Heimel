import { z } from "zod";
import { createRouter, publicQuery } from "./middleware";
import { listDrafts, updateDraftStatus } from "./queries/draftQueries";

export const queueRouter = createRouter({
  list: publicQuery
    .input(z.object({
      status: z.enum(["pending", "approved", "rejected", "posted"]).optional(),
    }).optional())
    .query(async ({ input }) => {
      return listDrafts(input?.status);
    }),

  approve: publicQuery
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input }) => {
      return updateDraftStatus(input.id, "approved");
    }),

  reject: publicQuery
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input }) => {
      return updateDraftStatus(input.id, "rejected");
    }),

  post: publicQuery
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input }) => {
      return updateDraftStatus(input.id, "posted");
    }),
});
