/**
 * VALO Learn Queries — Database operations for the self-learning system
 */

import { getDb } from "./connection";
import { referencePosts, postAnalysis, learnedPatterns, voiceProfile, draftFeedback } from "@db/schema";
import { eq, desc, sql, and, isNotNull } from "drizzle-orm";

// ── Reference Posts ───────────────────────────────────────────────

export async function createReferencePost(data: {
  source?: string;
  authorName?: string;
  authorLinkedInUrl?: string;
  content: string;
  metrics?: { likes?: number; comments?: number; shares?: number; impressions?: number };
  topic?: string;
  formatType?: string;
  postedAt?: Date;
}) {
  const db = getDb();
  const [result] = await db.insert(referencePosts).values({
    source: (data.source || "influencer") as any,
    authorName: data.authorName || null,
    authorLinkedInUrl: data.authorLinkedInUrl || null,
    content: data.content,
    metrics: data.metrics || null,
    topic: data.topic || null,
    formatType: (data.formatType || "text_post") as any,
    postedAt: data.postedAt || null,
  });
  return { id: Number(result.insertId) };
}

export async function listReferencePosts(opts?: { analyzed?: boolean; source?: string }) {
  const db = getDb();
  const conditions = [];

  if (opts?.analyzed === true) {
    conditions.push(isNotNull(referencePosts.analyzedAt));
  } else if (opts?.analyzed === false) {
    conditions.push(sql`${referencePosts.analyzedAt} IS NULL`);
  }

  if (opts?.source) {
    conditions.push(eq(referencePosts.source, opts.source as any));
  }

  if (conditions.length > 0) {
    return db.select().from(referencePosts).where(and(...conditions)).orderBy(desc(referencePosts.createdAt));
  }

  return db.select().from(referencePosts).orderBy(desc(referencePosts.createdAt));
}

export async function getUnanalyzedPosts(limit = 10) {
  const db = getDb();
  return db.select().from(referencePosts)
    .where(sql`${referencePosts.analyzedAt} IS NULL`)
    .orderBy(desc(referencePosts.createdAt))
    .limit(limit);
}

export async function markPostAnalyzed(id: number) {
  const db = getDb();
  await db.update(referencePosts)
    .set({ analyzedAt: new Date() })
    .where(eq(referencePosts.id, id));
  return { ok: true };
}

export async function getReferencePostById(id: number) {
  const db = getDb();
  const results = await db.select().from(referencePosts).where(eq(referencePosts.id, id)).limit(1);
  return results[0] || null;
}

export async function deleteReferencePost(id: number) {
  const db = getDb();
  await db.delete(referencePosts).where(eq(referencePosts.id, id));
  return { ok: true };
}

// ── Post Analysis ─────────────────────────────────────────────────

export async function createPostAnalysis(data: {
  referencePostId: number;
  hookType?: string;
  structureType?: string;
  emotionalTone?: string;
  successFactors?: any;
  voicePatterns?: any;
  keyInsights?: string;
  score?: number;
}) {
  const db = getDb();
  const [result] = await db.insert(postAnalysis).values({
    referencePostId: data.referencePostId,
    hookType: data.hookType || null,
    structureType: data.structureType || null,
    emotionalTone: data.emotionalTone || null,
    successFactors: data.successFactors || null,
    voicePatterns: data.voicePatterns || null,
    keyInsights: data.keyInsights || null,
    score: data.score ?? null,
  });
  return { id: Number(result.insertId) };
}

export async function listPostAnalyses() {
  const db = getDb();
  return db.select().from(postAnalysis).orderBy(desc(postAnalysis.createdAt));
}

export async function getAnalysisForPost(postId: number) {
  const db = getDb();
  const results = await db.select().from(postAnalysis)
    .where(eq(postAnalysis.referencePostId, postId))
    .limit(1);
  return results[0] || null;
}

// ── Learned Patterns ──────────────────────────────────────────────

export async function createLearnedPattern(data: {
  patternType: string;
  pattern: string;
  evidence?: any;
  confidence?: number;
}) {
  const db = getDb();
  const [result] = await db.insert(learnedPatterns).values({
    patternType: data.patternType as any,
    pattern: data.pattern,
    evidence: data.evidence || null,
    confidence: data.confidence ?? 0.5,
  });
  return { id: Number(result.insertId) };
}

export async function listLearnedPatterns(opts?: { patternType?: string; active?: boolean }) {
  const db = getDb();
  const conditions = [];

  if (opts?.patternType) {
    conditions.push(eq(learnedPatterns.patternType, opts.patternType as any));
  }

  if (opts?.active === true) {
    conditions.push(eq(learnedPatterns.isActive, "true" as any));
  }

  if (conditions.length > 0) {
    return db.select().from(learnedPatterns)
      .where(and(...conditions))
      .orderBy(desc(learnedPatterns.confidence));
  }

  return db.select().from(learnedPatterns).orderBy(desc(learnedPatterns.confidence));
}

export async function getActivePatternsForPrompt() {
  const db = getDb();
  return db.select({
    patternType: learnedPatterns.patternType,
    pattern: learnedPatterns.pattern,
  }).from(learnedPatterns)
    .where(eq(learnedPatterns.isActive, "true" as any))
    .orderBy(desc(learnedPatterns.confidence))
    .limit(20);
}

export async function incrementPatternUsage(id: number) {
  const db = getDb();
  await db.update(learnedPatterns)
    .set({
      usageCount: sql`${learnedPatterns.usageCount} + 1`,
      lastUsedAt: new Date(),
    })
    .where(eq(learnedPatterns.id, id));
  return { ok: true };
}

export async function deactivatePattern(id: number) {
  const db = getDb();
  await db.update(learnedPatterns)
    .set({ isActive: "false" as any })
    .where(eq(learnedPatterns.id, id));
  return { ok: true };
}

export async function deleteLearnedPattern(id: number) {
  const db = getDb();
  await db.delete(learnedPatterns).where(eq(learnedPatterns.id, id));
  return { ok: true };
}

// ── Voice Profile ─────────────────────────────────────────────────

export async function addVoiceEntry(data: {
  category: string;
  content: string;
  source?: string;
  confidence?: number;
}) {
  const db = getDb();
  const [result] = await db.insert(voiceProfile).values({
    category: data.category as any,
    content: data.content,
    source: (data.source || "auto_learned") as any,
    confidence: data.confidence ?? 0.5,
  });
  return { id: Number(result.insertId) };
}

export async function listVoiceProfile(opts?: { category?: string; source?: string }) {
  const db = getDb();
  const conditions = [];

  if (opts?.category) {
    conditions.push(eq(voiceProfile.category, opts.category as any));
  }

  if (opts?.source) {
    conditions.push(eq(voiceProfile.source, opts.source as any));
  }

  if (conditions.length > 0) {
    return db.select().from(voiceProfile)
      .where(and(...conditions))
      .orderBy(desc(voiceProfile.confidence));
  }

  return db.select().from(voiceProfile).orderBy(desc(voiceProfile.confidence));
}

export async function getVoiceProfileForPrompt() {
  const db = getDb();
  return db.select({
    category: voiceProfile.category,
    content: voiceProfile.content,
  }).from(voiceProfile)
    .orderBy(desc(voiceProfile.confidence))
    .limit(30);
}

export async function deleteVoiceEntry(id: number) {
  const db = getDb();
  await db.delete(voiceProfile).where(eq(voiceProfile.id, id));
  return { ok: true };
}

// ── Draft Feedback ────────────────────────────────────────────────

export async function createDraftFeedback(data: {
  draftId: number;
  linkedInPostUrl?: string;
  impressions?: number;
  likes?: number;
  comments?: number;
  shares?: number;
  commentQuality?: string;
  patternsUsed?: any;
  learnings?: string;
}) {
  const db = getDb();
  const [result] = await db.insert(draftFeedback).values({
    draftId: data.draftId,
    linkedInPostUrl: data.linkedInPostUrl || null,
    impressions: data.impressions ?? null,
    likes: data.likes ?? null,
    comments: data.comments ?? null,
    shares: data.shares ?? null,
    commentQuality: data.commentQuality || null,
    patternsUsed: data.patternsUsed || null,
    learnings: data.learnings || null,
  });
  return { id: Number(result.insertId) };
}

export async function listDraftFeedback() {
  const db = getDb();
  return db.select().from(draftFeedback).orderBy(desc(draftFeedback.createdAt));
}

// ── Stats ─────────────────────────────────────────────────────────

export async function getLearningStats() {
  const db = getDb();

  const postsCount = await db.select({ count: sql<number>`count(*)` }).from(referencePosts);
  const analyzedCount = await db.select({ count: sql<number>`count(*)` })
    .from(referencePosts)
    .where(isNotNull(referencePosts.analyzedAt));
  const patternsCount = await db.select({ count: sql<number>`count(*)` }).from(learnedPatterns);
  const voiceCount = await db.select({ count: sql<number>`count(*)` }).from(voiceProfile);
  const feedbackCount = await db.select({ count: sql<number>`count(*)` }).from(draftFeedback);

  return {
    totalPosts: postsCount[0]?.count || 0,
    analyzedPosts: analyzedCount[0]?.count || 0,
    totalPatterns: patternsCount[0]?.count || 0,
    voiceEntries: voiceCount[0]?.count || 0,
    feedbackEntries: feedbackCount[0]?.count || 0,
  };
}