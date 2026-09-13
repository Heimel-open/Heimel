import {
  mysqlTable,
  mysqlEnum,
  serial,
  varchar,
  text,
  timestamp,
  int,
  float,
  json,
} from "drizzle-orm/mysql-core";

// ── Drafts Queue ──────────────────────────────────────────────────
// Generated drafts waiting for Njål's approval
export const drafts = mysqlTable("drafts", {
  id: serial("id").primaryKey(),
  type: mysqlEnum("type", ["reply", "dm", "post", "analyze", "redteam"]).notNull(),
  author: varchar("author", { length: 255 }).notNull(),
  original: text("original"),
  draft: text("draft").notNull(),
  // VALO gate scores
  coherence: float("coherence").notNull(),
  vuScore: int("vu_score").notNull(),
  tavRegime: varchar("tav_regime", { length: 20 }).notNull(),
  combinedStatus: varchar("combined_status", { length: 10 }).notNull(),
  instruments: json("instruments"),
  mode: varchar("mode", { length: 10 }).default("standard"),
  status: mysqlEnum("status", ["pending", "approved", "rejected", "posted"]).default("pending"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

// ── Watchlist ─────────────────────────────────────────────────────
// People/companies to monitor and track
export const watchlist = mysqlTable("watchlist", {
  id: serial("id").primaryKey(),
  name: varchar("name", { length: 255 }).notNull(),
  company: varchar("company", { length: 255 }),
  linkedinUrl: varchar("linkedin_url", { length: 500 }),
  flag: mysqlEnum("flag", ["monitor", "engage", "avoid", "critical"]).default("monitor"),
  notes: text("notes"),
  lastInteraction: timestamp("last_interaction"),
  addedAt: timestamp("added_at").notNull().defaultNow(),
});

// ── Activity Log ──────────────────────────────────────────────────
// Complete WORM-style audit log of all AI actions
export const activityLog = mysqlTable("activity_log", {
  id: serial("id").primaryKey(),
  action: mysqlEnum("action", [
    "draft_created", "draft_approved", "draft_rejected", "draft_posted",
    "scan_run", "watchlist_added", "watchlist_updated", "profile_analyzed"
  ]).notNull(),
  entityId: int("entity_id"),
  entityType: varchar("entity_type", { length: 20 }),
  details: json("details"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

// ── Analytics ─────────────────────────────────────────────────────
// Daily/monthly engagement metrics
export const analytics = mysqlTable("analytics", {
  id: serial("id").primaryKey(),
  period: varchar("period", { length: 10 }).notNull(), // "daily" or "weekly"
  periodKey: varchar("period_key", { length: 20 }).notNull(), // "2026-06-13" or "2026-W24"
  draftsCreated: int("drafts_created").default(0),
  draftsApproved: int("drafts_approved").default(0),
  avgCoherence: float("avg_coherence"),
  avgLatencyMs: int("avg_latency_ms"),
  regimeBreakdown: json("regime_breakdown"),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
});

// ── Reference Posts ───────────────────────────────────────────────
// High-performing LinkedIn posts the AI learns from
export const referencePosts = mysqlTable("reference_posts", {
  id: serial("id").primaryKey(),
  source: mysqlEnum("source", ["njals_own", "influencer", "viral_post", "competitor"]).default("influencer"),
  authorName: varchar("author_name", { length: 255 }),
  authorLinkedInUrl: varchar("author_linkedin_url", { length: 500 }),
  content: text("content").notNull(),
  metrics: json("metrics"), // { likes, comments, shares, impressions }
  topic: varchar("topic", { length: 255 }),
  formatType: mysqlEnum("format_type", ["text_post", "carousel", "poll", "document", "video", "story"]).default("text_post"),
  postedAt: timestamp("posted_at"),
  analyzedAt: timestamp("analyzed_at"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

// ── Post Analysis ─────────────────────────────────────────────────
// AI-generated analysis of what made a post work
export const postAnalysis = mysqlTable("post_analysis", {
  id: serial("id").primaryKey(),
  referencePostId: int("reference_post_id").notNull(),
  hookType: varchar("hook_type", { length: 50 }),
  structureType: varchar("structure_type", { length: 50 }),
  emotionalTone: varchar("emotional_tone", { length: 50 }),
  successFactors: json("success_factors"), // array of identified factors
  voicePatterns: json("voice_patterns"), // phrasing patterns, vocab choices
  keyInsights: text("key_insights"),
  score: float("score"), // overall quality score 0-1
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

// ── Learned Patterns ──────────────────────────────────────────────
// Extracted, generalized patterns the AI has learned
export const learnedPatterns = mysqlTable("learned_patterns", {
  id: serial("id").primaryKey(),
  patternType: mysqlEnum("pattern_type", ["hook", "structure", "tone", "topic_angle", "format", "voice", "engagement"]).notNull(),
  pattern: text("pattern").notNull(),
  evidence: json("evidence"), // which posts support this pattern
  confidence: float("confidence").default(0.5),
  usageCount: int("usage_count").default(0),
  lastUsedAt: timestamp("last_used_at"),
  isActive: mysqlEnum("is_active", ["true", "false"]).default("true"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

// ── Voice Profile ─────────────────────────────────────────────────
// Njål's evolving voice model — learned from corrections and analysis
export const voiceProfile = mysqlTable("voice_profile", {
  id: serial("id").primaryKey(),
  category: mysqlEnum("category", ["phrasing", "pet_peeve", "strong_opinion", "banned_word", "signature_move", "correction", "preference"]).notNull(),
  content: text("content").notNull(),
  source: mysqlEnum("source", ["manual", "auto_learned", "correction_diff", "post_analysis"]).default("auto_learned"),
  confidence: float("confidence").default(0.5),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

// ── Draft Feedback ────────────────────────────────────────────────
// Performance feedback on posted drafts — fuels the learning loop
export const draftFeedback = mysqlTable("draft_feedback", {
  id: serial("id").primaryKey(),
  draftId: int("draft_id").notNull(),
  linkedInPostUrl: varchar("linkedin_post_url", { length: 500 }),
  impressions: int("impressions"),
  likes: int("likes"),
  comments: int("comments"),
  shares: int("shares"),
  commentQuality: varchar("comment_quality", { length: 20 }), // high/medium/low based on word count
  patternsUsed: json("patterns_used"),
  learnings: text("learnings"), // what this post taught us
  createdAt: timestamp("created_at").notNull().defaultNow(),
});
