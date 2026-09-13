import { relations } from "drizzle-orm";
import { referencePosts, postAnalysis } from "./schema";

export const referencePostsRelations = relations(referencePosts, ({ one }) => ({
  analysis: one(postAnalysis, {
    fields: [referencePosts.id],
    references: [postAnalysis.referencePostId],
  }),
}));

export const postAnalysisRelations = relations(postAnalysis, ({ one }) => ({
  post: one(referencePosts, {
    fields: [postAnalysis.referencePostId],
    references: [referencePosts.id],
  }),
}));
