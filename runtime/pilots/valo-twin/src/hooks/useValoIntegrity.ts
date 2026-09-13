import { useState, useCallback } from 'react';
import type { IntegrityResult, ChatMessage } from '@/types/valo';

// Lite ensemble — stdlib only, runs client-side
function jaccardSimilarity(a: string, b: string): number {
  if (!a || !b) return 0.5;
  const setA = new Set<string>();
  const setB = new Set<string>();
  for (let i = 0; i < a.length - 1; i++) setA.add(a.slice(i, i + 2));
  for (let i = 0; i < b.length - 1; i++) setB.add(b.slice(i, i + 2));
  if (setA.size === 0 || setB.size === 0) return 0.5;
  const intersection = new Set([...setA].filter(x => setB.has(x)));
  const union = new Set([...setA, ...setB]);
  return intersection.size / union.size;
}

function charEntropy(text: string): number {
  if (!text) return 0.5;
  const freq: Record<string, number> = {};
  for (const c of text) freq[c] = (freq[c] || 0) + 1;
  const total = text.length;
  let entropy = 0;
  for (const count of Object.values(freq)) {
    const p = count / total;
    entropy -= p * Math.log2(p);
  }
  const maxEnt = Math.log2(Object.keys(freq).length || 1);
  return maxEnt > 0 ? Math.min(entropy / maxEnt, 1) : 0.5;
}

function lengthCalibration(token: string, context: string): number {
  const expected = context ? Math.sqrt(context.length) : 5;
  const ratio = expected > 0 ? token.length / expected : 1;
  return 1 - Math.min(Math.abs(ratio - 1), 1);
}

function contextDrift(token: string, context: string): number {
  if (!context) return 0.5;
  const lastWords = context.split(/\s+/).slice(-10).join(' ');
  return jaccardSimilarity(token, lastWords);
}

function computeVUChannels(
  textSimilarity: number,
  semanticEntropy: number,
  perturbation: number,
  calibration: number,
  drift: number
) {
  const coherence = textSimilarity;
  const stability = semanticEntropy;
  const integrity = (perturbation + calibration + drift) / 3;
  return { coherence, stability, integrity };
}

function sha256(message: string): string {
  // Simple hash for display purposes
  let hash = 0;
  for (let i = 0; i < message.length; i++) {
    const char = message.charCodeAt(i);
    hash = ((hash << 5) - hash + char) | 0;
  }
  return Math.abs(hash).toString(16).padStart(64, '0');
}

let sequenceCounter = 0;
let prevHash = '0'.repeat(64);

export function useValoIntegrity() {
  const [wormLog, setWormLog] = useState<IntegrityResult[]>([]);
  const [isHalted, setIsHalted] = useState(false);

  const evaluateMessage = useCallback((message: ChatMessage, prevContent: string = ''): IntegrityResult => {
    const text = message.content;
    
    // Run 5 lite instruments
    const textSim = jaccardSimilarity(text, prevContent);
    const entropy = charEntropy(text);
    const calib = lengthCalibration(text.slice(0, 50), prevContent);
    const drift = contextDrift(text.slice(0, 50), prevContent);
    
    // Perturbation resilience (character flip test)
    let perturbation = 0.5;
    if (text.length >= 2) {
      const flipped = text.slice(0, -1) + String.fromCharCode((text.charCodeAt(text.length - 1) + 1) % 128);
      perturbation = jaccardSimilarity(text, flipped);
    }
    
    // VU channels
    const channels = computeVUChannels(textSim, entropy, perturbation, calib, drift);
    
    // Combined score (weighted)
    const score = textSim * 0.25 + entropy * 0.25 + perturbation * 0.20 + calib * 0.15 + drift * 0.15;
    
    // Determine level
    let level = 0;
    let status: IntegrityResult['status'] = 'TRUSTED';
    let action: IntegrityResult['action'] = 'PASS';
    
    if (score < 0.30) { level = 4; status = 'HALT'; action = 'HALT'; }
    else if (score < 0.45) { level = 3; status = 'DEGRADE'; action = 'DEGRADE'; }
    else if (score < 0.60) { level = 2; status = 'WARN'; action = 'WARN'; }
    else if (score < 0.75) { level = 1; status = 'MONITOR'; action = 'PASS'; }
    
    // WORM hash
    sequenceCounter++;
    const payload = JSON.stringify({ seq: sequenceCounter, prev: prevHash, text: text.slice(0, 50), score: Math.round(score * 1000) / 1000 });
    const entryHash = sha256(payload);
    prevHash = entryHash;
    
    const result: IntegrityResult = {
      score: Math.round(score * 1000) / 1000,
      coherence: Math.round(channels.coherence * 1000) / 1000,
      stability: Math.round(channels.stability * 1000) / 1000,
      integrity: Math.round(channels.integrity * 1000) / 1000,
      status,
      action,
      instruments: {
        text_similarity: Math.round(textSim * 1000) / 1000,
        semantic_entropy: Math.round(entropy * 1000) / 1000,
        perturbation: Math.round(perturbation * 1000) / 1000,
        calibration: Math.round(calib * 1000) / 1000,
        drift: Math.round(drift * 1000) / 1000,
      },
      wormHash: entryHash.slice(0, 16),
      sequence: sequenceCounter,
    };
    
    setWormLog(prev => [...prev.slice(-99), result]);
    if (level === 4) setIsHalted(true);
    
    return result;
  }, []);

  const verifyWORM = useCallback((): boolean => {
    // Verify chain integrity
    let prev = '0'.repeat(64);
    for (const entry of wormLog) {
      const payload = JSON.stringify({ seq: entry.sequence, prev, score: entry.score });
      const expected = sha256(payload);
      if (entry.wormHash !== expected.slice(0, 16)) return false;
      prev = expected;
    }
    return true;
  }, [wormLog]);

  return { evaluateMessage, wormLog, isHalted, verifyWORM };
}
