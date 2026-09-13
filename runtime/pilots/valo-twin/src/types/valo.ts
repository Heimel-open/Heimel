export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  integrity?: IntegrityResult;
}

export interface IntegrityResult {
  score: number;
  coherence: number;
  stability: number;
  integrity: number;
  status: 'TRUSTED' | 'MONITOR' | 'WARN' | 'DEGRADE' | 'HALT';
  action: 'PASS' | 'WARN' | 'DEGRADE' | 'HALT';
  instruments: Record<string, number>;
  wormHash: string;
  sequence: number;
}

export interface WORMEntry {
  sequence: number;
  timestamp: number;
  prevHash: string;
  entryHash: string;
  sourceId: string;
  distrustLevel: number;
  action: string;
  score: number;
  metadata: string;
}

export type DistrustLevel = 0 | 1 | 2 | 3 | 4;

export const LEVEL_NAMES: Record<number, string> = {
  0: 'TRUSTED',
  1: 'MONITOR',
  2: 'WARN',
  3: 'DEGRADE',
  4: 'HALT',
};

export const LEVEL_COLORS: Record<number, string> = {
  0: 'text-green-500',
  1: 'text-blue-400',
  2: 'text-yellow-400',
  3: 'text-orange-500',
  4: 'text-red-500',
};

export const STATUS_BG: Record<string, string> = {
  'TRUSTED': 'bg-green-500/20 border-green-500/30',
  'MONITOR': 'bg-blue-500/20 border-blue-500/30',
  'WARN': 'bg-yellow-500/20 border-yellow-500/30',
  'DEGRADE': 'bg-orange-500/20 border-orange-500/30',
  'HALT': 'bg-red-500/20 border-red-500/30',
};
