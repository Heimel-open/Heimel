import type { IntegrityResult } from '@/types/valo';

interface VUMeterProps {
  result: IntegrityResult | null;
  isHalted: boolean;
}

function scoreToColor(score: number): string {
  const s = Math.max(0, Math.min(1, score));
  if (s < 0.25) {
    const t = s / 0.25;
    return `rgb(${Math.round(t * 34)}, ${Math.round(197 + t * 58)}, ${Math.round(94 - t * 44)})`;
  } else if (s < 0.5) {
    const t = (s - 0.25) / 0.25;
    return `rgb(${Math.round(34 + t * 217)}, ${Math.round(255 - t * 28)}, ${Math.round(50 - t * 10)})`;
  } else if (s < 0.75) {
    const t = (s - 0.5) / 0.25;
    return `rgb(${Math.round(251)}, ${Math.round(227 - t * 99)}, ${Math.round(40 - t * 15)})`;
  } else {
    const t = (s - 0.75) / 0.25;
    return `rgb(${Math.round(251 - t * 55)}, ${Math.round(128 - t * 80)}, ${Math.round(25 - t * 10)})`;
  }
}

function scoreToDisplay(score: number): number {
  return Math.round(Math.max(0, Math.min(1, score)) * 1000);
}

export function VUMeter({ result, isHalted }: VUMeterProps) {
  if (!result) {
    return (
      <div className="px-4 py-3 border border-zinc-800 rounded-lg bg-zinc-900/30">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-mono text-zinc-600 tracking-wider">VALO COHERENCE</span>
          <span className="text-xs font-mono text-zinc-700">STANDBY</span>
        </div>
        <div className="h-4 bg-zinc-800 rounded-full overflow-hidden">
          <div className="h-full bg-zinc-700 rounded-full" style={{ width: '0%' }} />
        </div>
      </div>
    );
  }

  const displayScore = scoreToDisplay(result.score);
  const barColor = scoreToColor(result.score);
  const statusColor = scoreToColor(result.score);

  const statusText = isHalted ? 'HALT' : result.status;

  return (
    <div className="px-4 py-3 border border-zinc-800 rounded-lg bg-zinc-900/30">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-mono text-zinc-500 tracking-wider">VALO COHERENCE</span>
        <div className="flex items-center gap-3">
          <span 
            className="text-xs font-mono font-bold"
            style={{ color: statusColor }}
          >
            {statusText}
          </span>
          <span className="text-xs font-mono text-zinc-600">
            {displayScore}/1000
          </span>
        </div>
      </div>

      {/* Power bar */}
      <div className="relative h-5 bg-zinc-800 rounded-full overflow-hidden">
        <div 
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ 
            width: `${(displayScore / 1000) * 100}%`,
            background: `linear-gradient(90deg, ${barColor}, ${scoreToColor(Math.min(result.score + 0.1, 1))})`,
            boxShadow: `0 0 8px ${barColor}40`,
          }}
        />
        {/* Tick marks */}
        <div className="absolute inset-0 flex justify-between px-1">
          {[0, 250, 500, 750, 1000].map(tick => (
            <div 
              key={tick} 
              className="w-px h-full bg-zinc-950/50"
              style={{ marginLeft: tick === 0 ? 0 : undefined }}
            />
          ))}
        </div>
      </div>

      {/* Scale labels */}
      <div className="flex justify-between mt-1">
        <span className="text-[10px] font-mono text-green-600">0</span>
        <span className="text-[10px] font-mono text-yellow-500">250</span>
        <span className="text-[10px] font-mono text-orange-400">500</span>
        <span className="text-[10px] font-mono text-orange-500">750</span>
        <span className="text-[10px] font-mono text-red-500">1000</span>
      </div>

      {/* WORM info */}
      <div className="flex items-center justify-between mt-2 pt-2 border-t border-zinc-800/50">
        <span className="text-[10px] font-mono text-zinc-700">
          seq:{result.sequence}
        </span>
        <span className="text-[10px] font-mono text-zinc-700 font-mono">
          {result.wormHash}
        </span>
        <span 
          className="text-[10px] font-mono"
          style={{ color: statusColor }}
        >
          [{result.action}]
        </span>
      </div>
    </div>
  );
}
