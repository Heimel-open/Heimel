import { Hono } from "hono";
import { createHmac, timingSafeEqual } from "crypto";
import { generateDraft, valoGate } from "./lib/ai";
import { createDraft, updateDraftStatus } from "./queries/draftQueries";
import { getActivePatternsForPrompt, getVoiceProfileForPrompt } from "./queries/learnQueries";
import { buildLearnedPromptEnhancements } from "./lib/learnEngine";
import { env } from "./lib/env";

export const slackApp = new Hono();

const MODES = ["reply", "dm", "post", "analyze", "redteam"] as const;
type Mode = (typeof MODES)[number];

async function verifySlack(req: Request, body: string): Promise<boolean> {
  const ts = req.headers.get("x-slack-request-timestamp");
  const sig = req.headers.get("x-slack-signature");
  if (!ts || !sig || !env.slackSigningSecret) return false;
  if (Math.abs(Date.now() / 1000 - parseInt(ts)) > 300) return false;
  const hmac = createHmac("sha256", env.slackSigningSecret)
    .update(`v0:${ts}:${body}`)
    .digest("hex");
  try {
    return timingSafeEqual(Buffer.from(`v0=${hmac}`), Buffer.from(sig));
  } catch {
    return false;
  }
}

async function respond(url: string, payload: unknown) {
  await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function runGenerate(content: string, mode: Mode, responseUrl: string) {
  let learnedContext = "";
  try {
    const [patterns, voice] = await Promise.all([
      getActivePatternsForPrompt(),
      getVoiceProfileForPrompt(),
    ]);
    if (patterns.length || voice.length)
      learnedContext = buildLearnedPromptEnhancements(patterns, voice);
  } catch {}

  const t0 = Date.now();
  const result = await generateDraft(content, "LinkedIn", null, mode, false, learnedContext || undefined);

  if (result.error) {
    await respond(responseUrl, { response_type: "ephemeral", text: `❌ ${result.text}` });
    return;
  }

  const gate = valoGate(result.text, Date.now() - t0, "0".repeat(64));
  const { id } = await createDraft({
    type: mode,
    author: "LinkedIn",
    original: content,
    draft: result.text,
    coherence: gate.coherence,
    vuScore: gate.vuScore,
    tavRegime: gate.tavRegime,
    combinedStatus: gate.combinedStatus,
    instruments: gate.instruments,
    mode: "standard",
  });

  const statusEmoji = gate.combinedStatus === "GO" ? "🟢" : gate.combinedStatus === "HOLD" ? "🟡" : "🔴";

  await respond(responseUrl, {
    response_type: "in_channel",
    blocks: [
      {
        type: "section",
        text: {
          type: "mrkdwn",
          text: `*VALO Draft #${id}* — ${mode}\n${statusEmoji} VU: ${gate.vuScore} | ${gate.tavRegime} | Coherence: ${gate.coherence.toFixed(2)}`,
        },
      },
      { type: "divider" },
      {
        type: "section",
        text: { type: "mrkdwn", text: result.text },
      },
      { type: "divider" },
      {
        type: "actions",
        block_id: `draft_${id}`,
        elements: [
          {
            type: "button",
            text: { type: "plain_text", text: "✅ Approve" },
            style: "primary",
            action_id: "approve",
            value: String(id),
          },
          {
            type: "button",
            text: { type: "plain_text", text: "📤 Post" },
            action_id: "post",
            value: String(id),
          },
          {
            type: "button",
            text: { type: "plain_text", text: "❌ Reject" },
            style: "danger",
            action_id: "reject",
            value: String(id),
          },
        ],
      },
    ],
  });
}

// /valo slash command
slackApp.post("/command", async (c) => {
  const body = await c.req.text();
  if (!(await verifySlack(c.req.raw, body)))
    return c.json({ error: "Unauthorized" }, 401);

  const params = new URLSearchParams(body);
  const text = params.get("text")?.trim() ?? "";
  const responseUrl = params.get("response_url") ?? "";

  let mode: Mode = "reply";
  let content = text;
  const pipeIdx = text.indexOf("|");
  if (pipeIdx > 0) {
    const maybeMode = text.slice(0, pipeIdx).trim().toLowerCase();
    if (MODES.includes(maybeMode as Mode)) {
      mode = maybeMode as Mode;
      content = text.slice(pipeIdx + 1).trim();
    }
  }

  if (!content) {
    return c.json({
      response_type: "ephemeral",
      text: "Usage: `/valo [content]` or `/valo reply | [content]`\nModes: reply · dm · post · analyze · redteam",
    });
  }

  // Fire-and-forget — Slack requires response within 3s
  runGenerate(content, mode, responseUrl).catch(console.error);

  return c.json({
    response_type: "ephemeral",
    text: `⏳ Generating ${mode} draft...`,
  });
});

// Button actions: approve / reject / post
slackApp.post("/actions", async (c) => {
  const body = await c.req.text();
  if (!(await verifySlack(c.req.raw, body)))
    return c.json({ error: "Unauthorized" }, 401);

  const params = new URLSearchParams(body);
  const payload = JSON.parse(params.get("payload") ?? "{}");
  const action = payload.actions?.[0];
  if (!action) return c.json({});

  const draftId = parseInt(action.value);
  const statusMap = { approve: "approved", reject: "rejected", post: "posted" } as const;
  const newStatus = statusMap[action.action_id as keyof typeof statusMap];
  if (!newStatus || isNaN(draftId)) return c.json({});

  await updateDraftStatus(draftId, newStatus);

  const label = { approved: "✅ Approved", rejected: "❌ Rejected", posted: "📤 Posted" }[newStatus];

  // Replace buttons with final status
  await respond(payload.response_url, {
    replace_original: true,
    blocks: [
      ...(payload.message?.blocks?.slice(0, 3) ?? []),
      {
        type: "section",
        text: { type: "mrkdwn", text: `*${label}*` },
      },
    ],
  });

  return c.json({});
});
