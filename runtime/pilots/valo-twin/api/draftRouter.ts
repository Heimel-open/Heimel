import { z } from "zod";
import { createRouter, publicQuery } from "./middleware";
import { generateDraft, valoGate } from "./lib/ai";
import { createDraft } from "./queries/draftQueries";
import { getActivePatternsForPrompt, getVoiceProfileForPrompt } from "./queries/learnQueries";
import { buildLearnedPromptEnhancements } from "./lib/learnEngine";

async function fetchLearnedContext(): Promise<string> {
  try {
    const [patterns, voiceEntries] = await Promise.all([
      getActivePatternsForPrompt(),
      getVoiceProfileForPrompt(),
    ]);
    if (patterns.length === 0 && voiceEntries.length === 0) return "";
    return buildLearnedPromptEnhancements(patterns, voiceEntries);
  } catch {
    return "";
  }
}

export const draftRouter = createRouter({
  generate: publicQuery
    .input(z.object({
      comment: z.string().min(1),
      author: z.string().min(1),
      location: z.string().nullable(),
      mode: z.enum(["reply", "dm", "analyze", "redteam", "post"]).default("reply"),
      creative: z.boolean().default(false),
      prevHash: z.string().default("0".repeat(64)),
      useLearned: z.boolean().default(true),
    }))
    .mutation(async ({ input }) => {
      const t0 = Date.now();

      // Fetch learned patterns if enabled
      const learnedContext = input.useLearned ? await fetchLearnedContext() : "";

      const result = await generateDraft(
        input.comment,
        input.author,
        input.location,
        input.mode,
        input.creative,
        learnedContext || undefined,
      );

      if (result.error) {
        return { error: result.text, draft: null, learnedApplied: false };
      }

      const latency = Date.now() - t0;
      const gate = valoGate(result.text, latency, input.prevHash);

      // Store in DB
      const { id } = await createDraft({
        type: input.mode,
        author: input.author,
        original: input.comment,
        draft: result.text,
        coherence: gate.coherence,
        vuScore: gate.vuScore,
        tavRegime: gate.tavRegime,
        combinedStatus: gate.combinedStatus,
        instruments: gate.instruments,
        mode: input.creative ? "creative" : "standard",
      });

      return {
        error: null,
        draft: {
          id,
          text: result.text,
          ...gate,
          latencyMs: latency,
          mode: input.creative ? "creative" : "standard",
        },
        learnedApplied: !!learnedContext,
      };
    }),
});
