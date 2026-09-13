/**
 * VALO Learn Router — tRPC routes for the self-learning system
 */

import { z } from "zod";
import { createRouter, publicQuery } from "./middleware";
import {
  analyzePost,
  extractPatterns,
  buildVoiceProfile,
  buildLearnedPromptEnhancements,
  learnFromDraftPerformance,
  extractTopic,
} from "./lib/learnEngine";
import {
  createReferencePost,
  listReferencePosts,
  getUnanalyzedPosts,
  markPostAnalyzed,
  deleteReferencePost,
  createPostAnalysis,
  listPostAnalyses,
  getAnalysisForPost,
  createLearnedPattern,
  listLearnedPatterns,
  getActivePatternsForPrompt,
  deactivatePattern,
  deleteLearnedPattern,
  addVoiceEntry,
  listVoiceProfile,
  getVoiceProfileForPrompt,
  deleteVoiceEntry,
  createDraftFeedback,
  listDraftFeedback,
  getLearningStats,
} from "./queries/learnQueries";
import { getDb } from "./queries/connection";
import { referencePosts, postAnalysis } from "@db/schema";
import { eq, sql, desc } from "drizzle-orm";

export const learnRouter = createRouter({
  // ── Stats ─────────────────────────────────────────────────────
  stats: publicQuery.query(async () => {
    return getLearningStats();
  }),

  // ── Reference Posts ───────────────────────────────────────────
  posts: {
    list: publicQuery
      .input(z.object({
        analyzed: z.boolean().optional(),
        source: z.string().optional(),
      }).optional())
      .query(async ({ input }) => {
        return listReferencePosts(input || {});
      }),

    create: publicQuery
      .input(z.object({
        content: z.string().min(10),
        source: z.enum(["njals_own", "influencer", "viral_post", "competitor"]).optional(),
        authorName: z.string().optional(),
        authorLinkedInUrl: z.string().optional(),
        metrics: z.object({
          likes: z.number().optional(),
          comments: z.number().optional(),
          shares: z.number().optional(),
          impressions: z.number().optional(),
        }).optional(),
        topic: z.string().optional(),
        formatType: z.enum(["text_post", "carousel", "poll", "document", "video", "story"]).optional(),
      }))
      .mutation(async ({ input }) => {
        // Auto-extract topic if not provided
        let topic = input.topic;
        if (!topic && input.content.length > 20) {
          const extracted = await extractTopic(input.content);
          topic = extracted || undefined;
        }

        return createReferencePost({
          ...input,
          topic,
        });
      }),

    delete: publicQuery
      .input(z.object({ id: z.number() }))
      .mutation(async ({ input }) => {
        return deleteReferencePost(input.id);
      }),
  },

  // ── Analysis ──────────────────────────────────────────────────
  analyze: {
    run: publicQuery
      .input(z.object({ postId: z.number() }))
      .mutation(async ({ input }) => {
        const db = getDb();
        const posts = await db.select().from(referencePosts).where(eq(referencePosts.id, input.postId)).limit(1);
        const post = posts[0];
        if (!post) return { error: "Post not found", analysis: null };

        const analysis = await analyzePost(
          post.content,
          post.metrics as any || undefined
        );

        if (!analysis) return { error: "Analysis failed", analysis: null };

        const { id } = await createPostAnalysis({
          referencePostId: post.id,
          ...analysis,
        });

        await markPostAnalyzed(post.id);

        return { error: null, analysis: { id, ...analysis } };
      }),

    runAll: publicQuery
      .mutation(async () => {
        const unanalyzed = await getUnanalyzedPosts(20);
        const results = [];

        for (const post of unanalyzed) {
          const analysis = await analyzePost(
            post.content,
            post.metrics as any || undefined
          );

          if (analysis) {
            const { id } = await createPostAnalysis({
              referencePostId: post.id,
              ...analysis,
            });
            await markPostAnalyzed(post.id);
            results.push({ postId: post.id, analysisId: id, status: "analyzed" });
          } else {
            results.push({ postId: post.id, analysisId: null, status: "failed" });
          }
        }

        return { analyzed: results.length, results };
      }),

    list: publicQuery.query(async () => {
      return listPostAnalyses();
    }),

    forPost: publicQuery
      .input(z.object({ postId: z.number() }))
      .query(async ({ input }) => {
        return getAnalysisForPost(input.postId);
      }),
  },

  // ── Pattern Extraction ────────────────────────────────────────
  patterns: {
    list: publicQuery
      .input(z.object({
        patternType: z.string().optional(),
        activeOnly: z.boolean().optional(),
      }).optional())
      .query(async ({ input }) => {
        return listLearnedPatterns({
          patternType: input?.patternType,
          active: input?.activeOnly,
        });
      }),

    extract: publicQuery
      .mutation(async () => {
        // Get all analyses
        const analyses = await listPostAnalyses();
        if (analyses.length < 2) {
          return { error: "Need at least 2 analyzed posts to extract patterns", patterns: [] };
        }

        const engineAnalyses = analyses.map(a => ({
          hookType: a.hookType || "unknown",
          structureType: a.structureType || "unknown",
          emotionalTone: a.emotionalTone || "neutral",
          successFactors: a.successFactors as string[] || [],
          voicePatterns: a.voicePatterns as string[] || [],
          keyInsights: a.keyInsights || "",
          score: a.score || 0.5,
        }));

        const extracted = await extractPatterns(engineAnalyses);

        // Store new patterns
        const created = [];
        for (const p of extracted) {
          const { id } = await createLearnedPattern(p);
          created.push({ id, ...p });
        }

        return { error: null, patterns: created };
      }),

    deactivate: publicQuery
      .input(z.object({ id: z.number() }))
      .mutation(async ({ input }) => {
        return deactivatePattern(input.id);
      }),

    delete: publicQuery
      .input(z.object({ id: z.number() }))
      .mutation(async ({ input }) => {
        return deleteLearnedPattern(input.id);
      }),
  },

  // ── Voice Profile ─────────────────────────────────────────────
  voice: {
    list: publicQuery
      .input(z.object({
        category: z.string().optional(),
        source: z.string().optional(),
      }).optional())
      .query(async ({ input }) => {
        return listVoiceProfile(input || {});
      }),

    add: publicQuery
      .input(z.object({
        category: z.enum(["phrasing", "pet_peeve", "strong_opinion", "banned_word", "signature_move", "correction", "preference"]),
        content: z.string().min(1),
        source: z.enum(["manual", "auto_learned", "correction_diff", "post_analysis"]).optional(),
        confidence: z.number().min(0).max(1).optional(),
      }))
      .mutation(async ({ input }) => {
        return addVoiceEntry(input);
      }),

    build: publicQuery
      .mutation(async () => {
        // Get analyzed posts with high scores
        const db = getDb();
        const highScoringAnalyses = await db
          .select()
          .from(postAnalysis)
          .where(sql`${postAnalysis.score} >= 0.7`)
          .orderBy(desc(postAnalysis.score))
          .limit(20);

        if (highScoringAnalyses.length < 3) {
          return { error: "Need at least 3 high-scoring analyses to build voice profile", entries: [] };
        }

        // Get the actual post content for these analyses
        const contents: string[] = [];
        for (const analysis of highScoringAnalyses) {
          const posts = await db.select({ content: referencePosts.content })
            .from(referencePosts)
            .where(eq(referencePosts.id, analysis.referencePostId))
            .limit(1);
          if (posts[0]) contents.push(posts[0].content);
        }

        if (contents.length < 3) {
          return { error: "Not enough post content available", entries: [] };
        }

        const profile = await buildVoiceProfile(contents);
        if (!profile) {
          return { error: "Voice profile building failed", entries: [] };
        }

        // Store voice entries
        const entries = [];
        for (const item of profile.phrasings) {
          const { id } = await addVoiceEntry({ category: "phrasing", content: item, source: "auto_learned", confidence: 0.7 });
          entries.push({ id, category: "phrasing", content: item });
        }
        for (const item of profile.strongOpinions) {
          const { id } = await addVoiceEntry({ category: "strong_opinion", content: item, source: "auto_learned", confidence: 0.7 });
          entries.push({ id, category: "strong_opinion", content: item });
        }
        for (const item of profile.petPeeves) {
          const { id } = await addVoiceEntry({ category: "pet_peeve", content: item, source: "auto_learned", confidence: 0.6 });
          entries.push({ id, category: "pet_peeve", content: item });
        }
        for (const item of profile.bannedWords) {
          const { id } = await addVoiceEntry({ category: "banned_word", content: item, source: "auto_learned", confidence: 0.8 });
          entries.push({ id, category: "banned_word", content: item });
        }
        for (const item of profile.signatureMoves) {
          const { id } = await addVoiceEntry({ category: "signature_move", content: item, source: "auto_learned", confidence: 0.75 });
          entries.push({ id, category: "signature_move", content: item });
        }
        for (const item of profile.preferences) {
          const { id } = await addVoiceEntry({ category: "preference", content: item, source: "auto_learned", confidence: 0.65 });
          entries.push({ id, category: "preference", content: item });
        }

        return { error: null, entries };
      }),

    delete: publicQuery
      .input(z.object({ id: z.number() }))
      .mutation(async ({ input }) => {
        return deleteVoiceEntry(input.id);
      }),
  },

  // ── Prompt Enhancement ────────────────────────────────────────
  promptEnhancement: publicQuery.query(async () => {
    const [patterns, voiceEntries] = await Promise.all([
      getActivePatternsForPrompt(),
      getVoiceProfileForPrompt(),
    ]);

    if (patterns.length === 0 && voiceEntries.length === 0) {
      return { hasLearnings: false, enhancement: "" };
    }

    const enhancement = buildLearnedPromptEnhancements(patterns, voiceEntries);
    return { hasLearnings: true, enhancement };
  }),

  // ── Draft Feedback ────────────────────────────────────────────
  feedback: {
    create: publicQuery
      .input(z.object({
        draftId: z.number(),
        linkedInPostUrl: z.string().optional(),
        impressions: z.number().optional(),
        likes: z.number().optional(),
        comments: z.number().optional(),
        shares: z.number().optional(),
      }))
      .mutation(async ({ input }) => {
        // Auto-generate learnings if we have metrics
        let learnings: string | undefined;
        if (input.likes || input.comments) {
          const db = getDb();
          const drafts = await db.select({ content: referencePosts.content })
            .from(referencePosts)
            .where(eq(referencePosts.id, input.draftId))
            .limit(1);
          if (drafts[0]?.content) {
            const result = await learnFromDraftPerformance(drafts[0].content, {
              likes: input.likes,
              comments: input.comments,
              shares: input.shares,
            });
            learnings = result || undefined;
          }
        }

        return createDraftFeedback({ ...input, learnings });
      }),

    list: publicQuery.query(async () => {
      return listDraftFeedback();
    }),
  },
});