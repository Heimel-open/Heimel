/**
 * VALO Learn Engine — Self-Learning AI System
 *
 * Analyzes high-performing LinkedIn posts, extracts patterns,
 * builds an evolving voice profile, and enhances draft generation.
 */

import { env } from "./env";

const apiKey = env.geminiApiKey;

// ── Types ─────────────────────────────────────────────────────────

export interface PostMetrics {
  likes?: number;
  comments?: number;
  shares?: number;
  impressions?: number;
}

export interface PostAnalysis {
  hookType: string;
  structureType: string;
  emotionalTone: string;
  successFactors: string[];
  voicePatterns: string[];
  keyInsights: string;
  score: number;
}

export interface ExtractedPattern {
  patternType: "hook" | "structure" | "tone" | "topic_angle" | "format" | "voice" | "engagement";
  pattern: string;
  confidence: number;
}

// ── Analysis Prompt ───────────────────────────────────────────────

const ANALYSIS_PROMPT = `You are an expert LinkedIn content analyst. Analyze this LinkedIn post and extract what made it successful.

Provide your analysis as a JSON object with exactly these fields:
{
  "hookType": "The opening technique (e.g., 'contrarian', 'story', 'question', 'data_point', 'vulnerability', 'hot_take')",
  "structureType": "Post structure (e.g., 'hook-insight-CTA', 'story-lesson', 'listicle', 'problem-solution', 'mini_thread')",
  "emotionalTone": "Primary emotional register (e.g., 'confident_humble', 'curious', 'provocative', 'inspiring', 'pragmatic')",
  "successFactors": ["Array of 3-5 specific factors that drove engagement"],
  "voicePatterns": ["Array of 2-3 specific phrasing patterns, vocabulary choices, or stylistic signatures"],
  "keyInsights": "2-3 sentences summarizing the core strategic insight from this post",
  "score": 0.0
}

Score the post quality 0.0-1.0 based on:
- Hook strength (0-0.3)
- Structure clarity (0-0.2)
- Voice authenticity (0-0.2)
- Engagement potential (0-0.2)
- Value delivery (0-0.1)

Respond ONLY with the JSON object. No markdown, no code blocks.`;

// ── Pattern Extraction Prompt ─────────────────────────────────────

const PATTERN_EXTRACTION_PROMPT = `You are a pattern recognition expert. Given analyses of multiple successful LinkedIn posts, extract generalizable patterns.

Provide your response as a JSON array of patterns. Each pattern:
{
  "patternType": "hook|structure|tone|topic_angle|format|voice|engagement",
  "pattern": "Clear, actionable description of the pattern",
  "confidence": 0.0
}

Rules:
- Extract ONLY patterns supported by evidence in the analyses
- Confidence 0.0-1.0 based on frequency and consistency across posts
- Focus on what DIFFERENTIATES high performers from average posts
- Patterns should be SPECIFIC enough to replicate (not generic advice)
- Maximum 10 patterns, minimum 3

Respond ONLY with the JSON array. No markdown, no code blocks.`;

// ── Voice Learning Prompt ─────────────────────────────────────────

const VOICE_LEARNING_PROMPT = `You are a voice profiler. Given a collection of high-performing posts and their analyses, build a voice profile for the author.

Provide your response as a JSON object:
{
  "phrasings": ["Specific phrases or sentence constructions the author favors"],
  "strongOpinions": ["Positions or beliefs the author holds firmly"],
  "petPeeves": ["Things the author clearly dislikes or avoids"],
  "bannedWords": ["Words or phrases this author would NEVER use"],
  "signatureMoves": ["Unique stylistic techniques this author uses"],
  "preferences": ["Preferences in tone, length, format, topic approach"]
}

Each array should have 2-5 items, specific and actionable.

Respond ONLY with the JSON object. No markdown, no code blocks.`;

// ── Gemini Call Helper ────────────────────────────────────────────

async function callGemini(prompt: string, text: string): Promise<string> {
  if (!apiKey) return "{\"error\":\"GEMINI_API_KEY not set\"}";

  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`;
  const body = JSON.stringify({
    contents: [{ role: "user", parts: [{ text: `${prompt}\n\nPOST TO ANALYZE:\n${text}` }] }],
    generationConfig: { temperature: 0.3, maxOutputTokens: 2048 },
  });

  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
      });

      if (!res.ok) continue;

      const data = await res.json() as any;
      const candidates = data.candidates || [];
      if (!candidates.length) continue;

      const c = candidates[0];
      if (c.finishReason === "SAFETY" || c.finishReason === "RECITATION") continue;

      const parts = c.content?.parts || [];
      const text = parts[0]?.text || "";
      if (!text.trim()) continue;

      return text;
    } catch (e: any) {
      // retry
    }
  }

  return "{\"error\":\"API failed after 3 attempts\"}";
}

// ── Post Analysis ─────────────────────────────────────────────────

export async function analyzePost(content: string, metrics?: PostMetrics): Promise<PostAnalysis | null> {
  const metricsText = metrics
    ? `\nMETRICS: ${metrics.likes || 0} likes, ${metrics.comments || 0} comments, ${metrics.shares || 0} shares`
    : "";

  const response = await callGemini(ANALYSIS_PROMPT, content + metricsText);

  try {
    const cleaned = response.replace(/```json\s*/g, "").replace(/```\s*/g, "").trim();
    const parsed = JSON.parse(cleaned);

    if (parsed.error) return null;

    return {
      hookType: parsed.hookType || "unknown",
      structureType: parsed.structureType || "unknown",
      emotionalTone: parsed.emotionalTone || "neutral",
      successFactors: Array.isArray(parsed.successFactors) ? parsed.successFactors : [],
      voicePatterns: Array.isArray(parsed.voicePatterns) ? parsed.voicePatterns : [],
      keyInsights: parsed.keyInsights || "",
      score: typeof parsed.score === "number" ? Math.max(0, Math.min(1, parsed.score)) : 0.5,
    };
  } catch {
    return null;
  }
}

// ── Batch Pattern Extraction ──────────────────────────────────────

export async function extractPatterns(analyses: PostAnalysis[]): Promise<ExtractedPattern[]> {
  if (analyses.length < 2) return [];

  const analysesText = analyses.map((a, i) =>
    `ANALYSIS ${i + 1}:\nHook: ${a.hookType}\nStructure: ${a.structureType}\nTone: ${a.emotionalTone}\nSuccess: ${a.successFactors.join(", ")}\nVoice: ${a.voicePatterns.join(", ")}\nInsights: ${a.keyInsights}\nScore: ${a.score}`
  ).join("\n\n---\n\n");

  const response = await callGemini(PATTERN_EXTRACTION_PROMPT, analysesText);

  try {
    const cleaned = response.replace(/```json\s*/g, "").replace(/```\s*/g, "").trim();
    const parsed = JSON.parse(cleaned);

    if (!Array.isArray(parsed)) return [];

    return parsed
      .filter((p: any) => p.patternType && p.pattern)
      .map((p: any) => ({
        patternType: p.patternType as ExtractedPattern["patternType"],
        pattern: p.pattern,
        confidence: typeof p.confidence === "number" ? Math.max(0, Math.min(1, p.confidence)) : 0.5,
      }));
  } catch {
    return [];
  }
}

// ── Voice Profile Building ────────────────────────────────────────

export interface VoiceProfileData {
  phrasings: string[];
  strongOpinions: string[];
  petPeeves: string[];
  bannedWords: string[];
  signatureMoves: string[];
  preferences: string[];
}

export async function buildVoiceProfile(contents: string[]): Promise<VoiceProfileData | null> {
  if (contents.length < 2) return null;

  const text = contents.join("\n\n---\n\n");
  const response = await callGemini(VOICE_LEARNING_PROMPT, text);

  try {
    const cleaned = response.replace(/```json\s*/g, "").replace(/```\s*/g, "").trim();
    const parsed = JSON.parse(cleaned);

    return {
      phrasings: Array.isArray(parsed.phrasings) ? parsed.phrasings : [],
      strongOpinions: Array.isArray(parsed.strongOpinions) ? parsed.strongOpinions : [],
      petPeeves: Array.isArray(parsed.petPeeves) ? parsed.petPeeves : [],
      bannedWords: Array.isArray(parsed.bannedWords) ? parsed.bannedWords : [],
      signatureMoves: Array.isArray(parsed.signatureMoves) ? parsed.signatureMoves : [],
      preferences: Array.isArray(parsed.preferences) ? parsed.preferences : [],
    };
  } catch {
    return null;
  }
}

// ── Prompt Enhancement ────────────────────────────────────────────

export function buildLearnedPromptEnhancements(
  patterns: { patternType: string; pattern: string }[],
  voiceEntries: { category: string; content: string }[]
): string {
  const sections: string[] = [];

  // Group patterns by type
  const byType: Record<string, string[]> = {};
  for (const p of patterns) {
    if (!byType[p.patternType]) byType[p.patternType] = [];
    byType[p.patternType].push(p.pattern);
  }

  if (Object.keys(byType).length > 0) {
    sections.push("LEARNED PATTERNS FROM HIGH-PERFORMING POSTS:");
    for (const [type, items] of Object.entries(byType)) {
      sections.push(`  [${type.toUpperCase()}]`);
      items.forEach((item, i) => sections.push(`    ${i + 1}. ${item}`));
    }
  }

  // Voice entries
  const byCategory: Record<string, string[]> = {};
  for (const v of voiceEntries) {
    if (!byCategory[v.category]) byCategory[v.category] = [];
    byCategory[v.category].push(v.content);
  }

  if (Object.keys(byCategory).length > 0) {
    sections.push("\nVOICE PROFILE (AUTO-LEARNED):");
    for (const [cat, items] of Object.entries(byCategory)) {
      sections.push(`  [${cat.toUpperCase().replace(/_/g, " ")}]`);
      items.forEach((item, i) => sections.push(`    ${i + 1}. ${item}`));
    }
  }

  return sections.join("\n");
}

// ── Post Performance Learning ─────────────────────────────────────

export async function learnFromDraftPerformance(
  draftContent: string,
  metrics: PostMetrics
): Promise<string | null> {
  const prompt = `Given this LinkedIn post and its performance metrics, extract one key learning:

Post: ${draftContent}
Metrics: ${metrics.likes || 0} likes, ${metrics.comments || 0} comments, ${metrics.shares || 0} shares

Respond with ONE sentence (max 20 words) capturing the key learning. Be specific and actionable.`;

  const response = await callGemini(prompt, "");
  const cleaned = response.replace(/"/g, "").trim();
  return cleaned.length > 5 ? cleaned : null;
}

// ── Topic Extraction ──────────────────────────────────────────────

export async function extractTopic(content: string): Promise<string | null> {
  const prompt = `Classify this LinkedIn post into a single topic category (2-4 words max). Examples: "AI Safety", "Founder Journey", "Team Building", "Industry Trends", "Product Launch", "Leadership", "Technical Deep-Dive". Respond with ONLY the topic, nothing else.`;

  const response = await callGemini(prompt, content);
  const cleaned = response.trim().split("\n")[0].trim();
  return cleaned.length > 0 && cleaned.length < 100 ? cleaned : null;
}