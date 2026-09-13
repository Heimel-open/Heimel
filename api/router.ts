import { createRouter, publicQuery } from "./middleware";
import { draftRouter } from "./draftRouter";
import { queueRouter } from "./queueRouter";
import { watchlistRouter } from "./watchlistRouter";
import { analyticsRouter } from "./analyticsRouter";
import { learnRouter } from "./learnRouter";

export const appRouter = createRouter({
  ping: publicQuery.query(() => ({ ok: true, ts: Date.now() })),
  draft: draftRouter,
  queue: queueRouter,
  watchlist: watchlistRouter,
  analytics: analyticsRouter,
  learn: learnRouter,
});

export type AppRouter = typeof appRouter;
