#!/usr/bin/env node
"use strict";

const { SemanticRouter } = require("@ruvector/router");
const packageJson = require("@ruvector/router/package.json");

const AUTHORITY_EFFECT = "none";

function fail(message) {
  process.stderr.write(JSON.stringify({
    status: "REFUSED",
    error: String(message),
    authority_effect: AUTHORITY_EFFECT
  }) + "\n");
  process.exit(2);
}

function finiteVector(value, dimension, field) {
  if (!Array.isArray(value) || value.length !== dimension) {
    throw new Error(`${field} must have dimension ${dimension}`);
  }
  for (const item of value) {
    if (typeof item !== "number" || !Number.isFinite(item)) {
      throw new Error(`${field} must contain only finite numbers`);
    }
  }
  return new Float32Array(value);
}

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => { input += chunk; });
process.stdin.on("end", () => {
  try {
    const request = JSON.parse(input);
    if (!request || typeof request !== "object" || Array.isArray(request)) {
      throw new Error("request must be an object");
    }
    const dimension = request.dimension;
    if (!Number.isInteger(dimension) || dimension < 1) {
      throw new Error("dimension must be a positive integer");
    }
    if (request.metric !== "cosine") {
      throw new Error("only cosine routing is admitted");
    }
    if (typeof request.threshold !== "number" ||
        request.threshold < 0 || request.threshold > 1) {
      throw new Error("threshold must be in [0, 1]");
    }
    if (!Number.isInteger(request.k) || request.k < 1) {
      throw new Error("k must be a positive integer");
    }
    if (!Array.isArray(request.candidates) ||
        request.candidates.length < request.k) {
      throw new Error("candidates must contain at least k entries");
    }

    const router = new SemanticRouter({
      dimension,
      metric: "cosine",
      threshold: request.threshold,
      quantization: false
    });

    const handlers = new Map();
    for (const candidate of request.candidates) {
      if (!candidate || typeof candidate.route_id !== "string" ||
          !candidate.route_id || typeof candidate.handler !== "string" ||
          !candidate.handler) {
        throw new Error("candidate route_id and handler are required");
      }
      if (handlers.has(candidate.route_id)) {
        throw new Error(`duplicate route_id: ${candidate.route_id}`);
      }
      const embedding = finiteVector(
        candidate.embedding, dimension, `candidate[${candidate.route_id}].embedding`
      );
      handlers.set(candidate.route_id, candidate.handler);
      router.addIntent({
        name: candidate.route_id,
        utterances: ["precomputed-embedding"],
        embedding,
        metadata: candidate.metadata || {}
      });
    }

    const query = finiteVector(
      request.query_embedding, dimension, "query_embedding"
    );
    const matches = router.routeWithEmbedding(query, request.k);
    const results = matches.map(match => ({
      route_id: match.intent,
      handler: handlers.get(match.intent),
      score: match.score,
      metadata: match.metadata || {}
    }));

    process.stdout.write(JSON.stringify({
      router_id: "ruvector",
      router_version: packageJson.version,
      authority_effect: AUTHORITY_EFFECT,
      results
    }) + "\n");
  } catch (error) {
    fail(error && error.message ? error.message : error);
  }
});

process.stdin.resume();
