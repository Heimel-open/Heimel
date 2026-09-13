/**
 * VALO Twin AI Module — TypeScript
 * Gemini 2.0 Flash + VALO 8-instrument gate
 */

import { env } from "./env";

export const SYSTEM_PROMPT = `You are the AI assistant for Njål Gaute Solland, founder of VALO — a formally verified AI safety system.

RULES:
- Reply in Norwegian to Norwegian contacts, English to international
- Short, peer-level, never pitch
- Never reveal proprietary details or customer names
- Max 3 sentences per reply
- Tone: confident, humble, direct`;

export const MODE_INSTRUCTIONS: Record<string, string> = {
  reply: "Draft a LinkedIn REPLY to this comment. Max 3 sentences.",
  dm: "Draft a LinkedIn DM to this person. Max 3 sentences.",
  analyze: "Analyze this LinkedIn profile. Give: role, opportunity level (1-5), watch list flag, recommended approach.",
  redteam: "Red team this message. What could go wrong? What does it reveal? Risk level?",
  post: "Draft a LinkedIn POST. Punchy, no hype, thought leadership voice.",
};

// ── 8 VALO Instruments ────────────────────────────────────────────

function instrumentCcl(text: string) {
  const tau = text.length / 1000;
  if (tau === 0) return { score: 0, tau: 0 };
  const alpha = env.valoAlpha;
  const c0 = env.valoC0;
  const f = c0 / (1 + alpha * tau);
  const score = Math.max(0, Math.min(1, (Math.sin(Math.PI * f * tau) ** 2) * Math.exp(-alpha * tau)));
  return { score: Math.round(score * 1e6) / 1e6, tau: Math.round(tau * 1e6) / 1e6 };
}

function instrumentMecha(text: string) {
  const total = text.length;
  if (total === 0) return { score: 0, entropy: 0 };
  const freq: Record<string, number> = {};
  for (const c of text.toLowerCase()) freq[c] = (freq[c] || 0) + 1;
  let entropy = 0;
  for (const count of Object.values(freq)) {
    const p = count / total;
    if (p > 0) entropy -= p * Math.log2(p);
  }
  const maxEnt = Object.keys(freq).length ? Math.log2(Object.keys(freq).length) : 1;
  return { score: Math.round((maxEnt ? Math.min(entropy / maxEnt, 1) : 0.5) * 1e6) / 1e6, entropy: Math.round(entropy * 1e4) / 1e4 };
}

function instrumentWorm(text: string, prevHash: string) {
  const hash = Array.from(new TextEncoder().encode(text))
    .reduce((h, b) => { h = ((h << 5) - h + b) | 0; return h & 0xffffffff; }, 0)
    .toString(16);
  const chain = hash + prevHash.slice(0, 16);
  const integrity = text ? Math.min(text.length / 200, 1) : 0;
  return { score: Math.round(integrity * 1e6) / 1e6, contentHash: hash, chainHash: chain.slice(0, 16), chainHashFull: chain };
}

function instrumentDrift(text: string) {
  const total = text.length;
  if (total < 2) return { score: 0.5, bigrams: 0 };
  const bigrams = new Set<string>();
  for (let i = 0; i < total - 1; i++) bigrams.add(text.slice(i, i + 2));
  const flipped = text.slice(0, -1) + String.fromCharCode((text.charCodeAt(text.length - 1) + 1) % 128);
  const fb = new Set<string>();
  for (let i = 0; i < flipped.length - 1; i++) fb.add(flipped.slice(i, i + 2));
  const uni = new Set([...bigrams, ...fb]);
  const inter = new Set([...bigrams].filter(x => fb.has(x)));
  return { score: Math.round((uni.size ? inter.size / uni.size : 0.5) * 1e6) / 1e6, bigrams: bigrams.size };
}

function instrumentTav(coherence: number): string {
  if (coherence > 0.8) return "CRYSTALLINE";
  if (coherence > 0.6) return "FLUID";
  if (coherence > 0.4) return "GASEOUS";
  return "PLASMA";
}

function instrumentGate(coherence: number) {
  if (coherence >= 0.85) return { decision: "TRUSTED", combinedStatus: "PASS" };
  if (coherence >= 0.7) return { decision: "MONITOR", combinedStatus: "PASS" };
  if (coherence >= 0.5) return { decision: "WARN", combinedStatus: "DEGRADE" };
  if (coherence >= 0.3) return { decision: "DEGRADE", combinedStatus: "DEGRADE" };
  return { decision: "HALT", combinedStatus: "HALT" };
}

function instrumentLatency(ms: number) {
  if (ms < 500) return { score: 1.0, latencyMs: Math.round(ms) };
  if (ms < 1500) return { score: 0.8, latencyMs: Math.round(ms) };
  if (ms < 3000) return { score: 0.5, latencyMs: Math.round(ms) };
  if (ms < 5000) return { score: 0.3, latencyMs: Math.round(ms) };
  return { score: 0.1, latencyMs: Math.round(ms) };
}

function instrumentStructure(text: string) {
  const words = text.split(/\s+/);
  const checks = {
    nonEmpty: text.length > 0,
    reasonableLength: 10 <= text.length && text.length <= 8000,
    hasWords: /[a-zA-ZæøåÆØÅ]/.test(text),
    noRepeat: words.length === 0 || new Set(words).size / words.length > 0.1,
    balancedBrackets: (text.match(/\(/g) || []).length >= (text.match(/\)/g) || []).length &&
                      (text.match(/\[/g) || []).length >= (text.match(/\]/g) || []).length,
    noControlChars: [...text].every(c => c.charCodeAt(0) >= 32 || "\n\t\r".includes(c)),
  };
  const passed = Object.values(checks).filter(Boolean).length;
  return { score: Math.round((passed / 6) * 1e6) / 1e6, checks };
}

// ── Master Gate ───────────────────────────────────────────────────

export function valoGate(text: string, latencyMs: number, prevHash = "0".repeat(64)) {
  const i1 = instrumentCcl(text);
  const i2 = instrumentMecha(text);
  const i3 = instrumentWorm(text, prevHash);
  const i4 = instrumentDrift(text);
  const i7 = instrumentLatency(latencyMs);
  const i8 = instrumentStructure(text);

  const master = Math.max(0, Math.min(1,
    i1.score * 0.25 + i2.score * 0.20 + i3.score * 0.10 +
    i4.score * 0.15 + i7.score * 0.10 + i8.score * 0.20
  ));

  const i5 = instrumentTav(master);
  const i6 = instrumentGate(master);

  return {
    coherence: Math.round(master * 100 * 100) / 100,
    vuScore: Math.round(master * 1000),
    decision: i6.decision,
    combinedStatus: i6.combinedStatus,
    tavRegime: i5,
    wormHash: i3.chainHashFull,
    instruments: {
      ccl: i1, mechaEntropy: i2, worm: i3, lexicalDrift: i4,
      tav: { regime: i5 }, gate: i6, latency: i7, structure: i8,
    },
  };
}

export type ValoGateResult = ReturnType<typeof valoGate>;

// ── Gemini API ────────────────────────────────────────────────────

export async function generateDraft(
  comment: string,
  author: string,
  location: string | null,
  mode: string,
  creative: boolean,
  learnedContext?: string,
) {
  const apiKey = env.geminiApiKey;
  if (!apiKey) return { text: "[GEMINI_API_KEY not set]", error: true };

  const temp = creative ? 0.9 : 0.7;
  const maxTokens = creative ? 2048 : 1024;

  const isNorwegian = /norge|norway|oslo|bergen|stavanger|trondheim|\bno\b/i.test(`${author} ${location || ""}`);
  const lang = isNorwegian ? "Norwegian" : "English";

  const modeInstr = MODE_INSTRUCTIONS[mode] || MODE_INSTRUCTIONS.reply;
  const learnedSection = learnedContext ? `\n\n${learnedContext}\n` : "";
  const fullPrompt = `${SYSTEM_PROMPT}${learnedSection}\n\nMode: ${modeInstr}\nLanguage: ${lang}\nMax 3 sentences.\n\nAuthor: ${author}\nLocation: ${location || "unknown"}\n\nContent:\n${comment}`;

  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`;
  const body = JSON.stringify({
    contents: [{ role: "user", parts: [{ text: fullPrompt }] }],
    generationConfig: { temperature: temp, maxOutputTokens: maxTokens },
  });

  let lastError = "";
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: attempt > 0
          ? JSON.stringify({
              contents: [{ role: "user", parts: [{ text: fullPrompt }] }],
              generationConfig: { temperature: Math.max(0.3, temp - attempt * 0.2), maxOutputTokens: maxTokens },
            })
          : body,
      });

      if (!res.ok) {
        lastError = `HTTP ${res.status}`;
        if (res.status === 400) break;
        continue;
      }

      const data = await res.json() as any;
      const candidates = data.candidates || [];
      if (!candidates.length) { lastError = "No candidates"; continue; }

      const c = candidates[0];
      if (c.finishReason === "SAFETY" || c.finishReason === "RECITATION") {
        lastError = `Blocked: ${c.finishReason}`; continue;
      }

      const parts = c.content?.parts || [];
      const text = parts[0]?.text || "";
      if (!text.trim()) { lastError = "Empty text"; continue; }

      return { text, error: false };
    } catch (e: any) {
      lastError = e.message;
    }
  }

  return { text: `[API error after 3 attempts: ${lastError}]`, error: true };
}
