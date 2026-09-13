import { getDb } from "./connection";
import { drafts, watchlist, activityLog } from "@db/schema";
import { eq, desc, sql } from "drizzle-orm";

// ── Draft Operations ──────────────────────────────────────────────

export async function createDraft(data: {
  type: string;
  author: string;
  original?: string;
  draft: string;
  coherence: number;
  vuScore: number;
  tavRegime: string;
  combinedStatus: string;
  instruments?: any;
  mode: string;
}) {
  const db = getDb();
  const [result] = await db.insert(drafts).values({
    type: data.type as any,
    author: data.author,
    original: data.original || null,
    draft: data.draft,
    coherence: data.coherence,
    vuScore: data.vuScore,
    tavRegime: data.tavRegime,
    combinedStatus: data.combinedStatus,
    instruments: data.instruments || null,
    mode: data.mode,
  });
  
  // Log activity
  await db.insert(activityLog).values({
    action: "draft_created",
    entityId: Number(result.insertId),
    entityType: "draft",
    details: { coherence: data.coherence, regime: data.tavRegime },
  });
  
  return { id: Number(result.insertId) };
}

export async function listDrafts(status?: string) {
  const db = getDb();
  if (status) {
    return db.select().from(drafts).where(eq(drafts.status, status as any)).orderBy(desc(drafts.createdAt));
  }
  return db.select().from(drafts).orderBy(desc(drafts.createdAt));
}

export async function updateDraftStatus(id: number, status: string) {
  const db = getDb();
  await db.update(drafts).set({ status: status as any }).where(eq(drafts.id, id));
  
  await db.insert(activityLog).values({
    action: status === "approved" ? "draft_approved" : status === "rejected" ? "draft_rejected" : "draft_posted",
    entityId: id,
    entityType: "draft",
  });
  
  return { ok: true };
}

// ── Watchlist Operations ──────────────────────────────────────────

export async function listWatchlist() {
  const db = getDb();
  return db.select().from(watchlist).orderBy(desc(watchlist.addedAt));
}

export async function addWatchlistEntry(data: {
  name: string;
  company?: string;
  linkedinUrl?: string;
  flag?: string;
  notes?: string;
}) {
  const db = getDb();
  const [result] = await db.insert(watchlist).values({
    name: data.name,
    company: data.company || null,
    linkedinUrl: data.linkedinUrl || null,
    flag: (data.flag || "monitor") as any,
    notes: data.notes || null,
  });
  
  await db.insert(activityLog).values({
    action: "watchlist_added",
    entityId: Number(result.insertId),
    entityType: "watchlist",
  });
  
  return { id: Number(result.insertId) };
}

export async function updateWatchlistFlag(id: number, flag: string) {
  const db = getDb();
  await db.update(watchlist).set({ flag: flag as any }).where(eq(watchlist.id, id));
  await db.insert(activityLog).values({
    action: "watchlist_updated",
    entityId: id,
    entityType: "watchlist",
  });
  return { ok: true };
}

// ── Analytics Operations ──────────────────────────────────────────

export async function getStats() {
  const db = getDb();
  
  const allDrafts = await db.select().from(drafts);
  const pending = allDrafts.filter(d => d.status === "pending").length;
  const approved = allDrafts.filter(d => d.status === "approved").length;
  const rejected = allDrafts.filter(d => d.status === "rejected").length;
  const posted = allDrafts.filter(d => d.status === "posted").length;
  
  const avgCoherence = allDrafts.length
    ? Math.round(allDrafts.reduce((sum, d) => sum + d.coherence, 0) / allDrafts.length * 100) / 100
    : 0;
  
  const regimeBreakdown = allDrafts.reduce((acc, d) => {
    acc[d.tavRegime] = (acc[d.tavRegime] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
  const watchlistCount = await db.select({ count: sql<number>`count(*)` }).from(watchlist);
  
  return {
    totalDrafts: allDrafts.length,
    pending,
    approved,
    rejected,
    posted,
    avgCoherence,
    regimeBreakdown,
    watchlistCount: watchlistCount[0]?.count || 0,
  };
}

export async function getRecentActivity(limit = 20) {
  const db = getDb();
  return db.select().from(activityLog).orderBy(desc(activityLog.createdAt)).limit(limit);
}
