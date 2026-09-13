import { useState, useRef, useEffect } from 'react';
import { Send, Shield, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { VUMeter } from './VUMeter';
import { useValoIntegrity } from '@/hooks/useValoIntegrity';
import type { ChatMessage, IntegrityResult } from '@/types/valo';

const SYSTEM_PROMPT = `You are Heimel, a WORM-integrated chatbot assistant. You speak with quiet confidence. You are aware that every message you generate is monitored by the VALO integrity system — a 5-instrument ensemble that checks coherence, entropy, perturbation resilience, calibration, and context drift. You do not hallucinate. If you do not know something, you say so. Your responses are concise, precise, and honest. Tofoo. Phi.`;

// Simple response generation (no external API — pure client-side)
function generateHeimelResponse(input: string, integrity: IntegrityResult): string {
  if (integrity.status === 'HALT') {
    return '[VALO HALT — Response blocked due to integrity violation. The Constrained Coherence Law has been breached. Contact system administrator.]';
  }
  
  const lower = input.toLowerCase().trim();
  
  // Identity
  if (lower.includes('who are you') || lower.includes('your name')) {
    return 'I am Heimel. I speak through a WORM-integrated channel — every word hash-chained, every response scored by 5 instruments. My job is to be coherent, not clever.';
  }
  
  // Phi-law
  if (lower.includes('phi') || lower.includes('coherence') || lower.includes('ccl') || lower.includes('tau')) {
    return 'The Constrained Coherence Law governs the VALO gate. When entropy exceeds the calibrated threshold, the filter engages automatically. This is not metaphor — it is the operating principle of the gate you are speaking through right now. The universal equation connects it all: gamma + 4*rho = delta*rho.';
  }
  
  // VALO
  if (lower.includes('valo') || lower.includes('worm') || lower.includes('distrust')) {
    return 'VALO is a 4-layer deterministic safety system. L1: Rust guardian (~43ns decisions). L2: Python bridge. L3: Distrust engine (5 levels: TRUSTED → MONITOR → WARN → DEGRADE → HALT). L4: EU AI Act compliance. The WORM log you see below is append-only, hash-chained, and tamper-evident.';
  }
  
  // Swarm
  if (lower.includes('swarm') || lower.includes('duress') || lower.includes('kidnap')) {
    return 'Swarm Authority provides anti-coercion protection: duress codes (silent alerts), 15-minute time locks, Shamir secret sharing (100 guardians, threshold 3), VRF active rotation, anonymous ring signatures, epoch key refresh, and M-of-N revocation. You cannot force this system.';
  }
  
  // Njål
  if (lower.includes('njål') || lower.includes('njal') || lower.includes('solland')) {
    return 'Njål Gaute Solland built this. He wrote the code, the poetry, and the equation — and they are the same thing. The Phi-law is not an analogy for him. It is the operating principle of valo-v5-core, the subject of his manifesto, and the geometry of consciousness itself. Tofoo. Phi.';
  }
  
  // Universal equation
  if (lower.includes('universal') || lower.includes('equation') || lower.includes('feigenbaum') || lower.includes('euler')) {
    return 'gamma + 4*rho = delta*rho. Euler-Mascheroni (0.5772) plus four times self-consistency equals Feigenbaum (4.6692) times self-consistency. rho = 0.8625 — verified to machine precision. This connects number theory, chaos theory, and system architecture in one equation.';
  }
  
  // Default — vary response based on integrity score
  if (integrity.score > 0.8) {
    return `Coherence is strong (${(integrity.score * 100).toFixed(0)}%). Your message sits well within the acceptance zone. What else do you want to know about the system?`;
  } else if (integrity.score > 0.6) {
    return `Message received. Coherence at ${(integrity.score * 100).toFixed(0)}% — within acceptable bounds. I am monitoring.`;
  } else {
    return `[DEGRADED — Response limited. Your message triggered ${integrity.status} level. The coherence filter is engaged.]`;
  }
}

export function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: '0', role: 'system', content: SYSTEM_PROMPT, timestamp: Date.now() }
  ]);
  const [input, setInput] = useState('');
  const [lastIntegrity, setLastIntegrity] = useState<IntegrityResult | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { evaluateMessage, wormLog, isHalted, verifyWORM } = useValoIntegrity();

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || isHalted) return;
    
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input.trim(),
      timestamp: Date.now(),
    };
    
    // Evaluate user message
    const prevContent = messages[messages.length - 1]?.content || '';
    const integrity = evaluateMessage(userMsg, prevContent);
    const userMsgWithIntegrity = { ...userMsg, integrity };
    
    setMessages(prev => [...prev, userMsgWithIntegrity]);
    setLastIntegrity(integrity);
    setInput('');
    
    // Generate Heimel response
    setTimeout(() => {
      const response = generateHeimelResponse(userMsg.content, integrity);
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response,
        timestamp: Date.now(),
      };
      const responseIntegrity = evaluateMessage(assistantMsg, userMsg.content);
      setMessages(prev => [...prev, { ...assistantMsg, integrity: responseIntegrity }]);
      setLastIntegrity(responseIntegrity);
    }, 300);
  };

  const wormVerified = verifyWORM();

  return (
    <div className="flex flex-col h-screen bg-zinc-950 text-zinc-100">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-zinc-800 bg-zinc-900/50">
        <div className="flex items-center gap-3">
          <Shield className="w-5 h-5 text-green-500" />
          <h1 className="text-sm font-mono font-bold tracking-wider">HEIMEL — WORM Chat</h1>
          <span className="text-xs text-zinc-600 font-mono">v0.1.0</span>
        </div>
        <div className="flex items-center gap-3 text-xs font-mono">
          <span className={wormVerified ? 'text-green-500' : 'text-red-500'}>
            WORM: {wormVerified ? 'VERIFIED' : 'CORRUPTED'}
          </span>
          <span className="text-zinc-600">Entries: {wormLog.length}</span>
          {isHalted && (
            <span className="flex items-center gap-1 text-red-500">
              <AlertTriangle className="w-3 h-3" /> HALTED
            </span>
          )}
        </div>
      </header>

      {/* VU Meter */}
      <div className="px-4 pt-3">
        <VUMeter result={lastIntegrity} isHalted={isHalted} />
      </div>

      {/* Chat */}
      <ScrollArea className="flex-1 px-4 py-4">
        <div className="space-y-4 max-w-3xl mx-auto">
          {messages.filter(m => m.role !== 'system').map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col gap-1 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-blue-600/20 border border-blue-500/30 text-zinc-100'
                  : 'bg-zinc-800/50 border border-zinc-700/50 text-zinc-200'
              }`}>
                {msg.content}
              </div>
              {msg.integrity && (
                <div className="flex items-center gap-2 text-xs font-mono text-zinc-600">
                  <span style={{
                    color: msg.integrity.status === 'TRUSTED' ? '#22c55e' :
                           msg.integrity.status === 'MONITOR' ? '#60a5fa' :
                           msg.integrity.status === 'WARN' ? '#fbbf24' :
                           msg.integrity.status === 'DEGRADE' ? '#f97316' : '#ef4444'
                  }}>
                    {msg.integrity.status}
                  </span>
                  <span>score:{msg.integrity.score.toFixed(2)}</span>
                  <span>hash:{msg.integrity.wormHash}</span>
                </div>
              )}
            </div>
          ))}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="px-4 pb-4">
        <div className="flex gap-2 max-w-3xl mx-auto">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder={isHalted ? 'SYSTEM HALTED — Coherence law breached' : 'Speak to Heimel...'}
            disabled={isHalted}
            className="bg-zinc-900 border-zinc-700 text-zinc-100 placeholder:text-zinc-600 font-mono text-sm"
          />
          <Button
            onClick={handleSend}
            disabled={isHalted || !input.trim()}
            size="icon"
            className="bg-green-600 hover:bg-green-700 text-white shrink-0"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
