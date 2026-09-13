import { useState } from 'react'
import { trpc } from '@/providers/trpc'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toast } from 'sonner'
import {
  PenTool, Loader2, Shield, Zap, Sparkles, Brain,
} from 'lucide-react'

export default function DraftPage() {
  const [author, setAuthor] = useState('')
  const [location, setLocation] = useState('')
  const [comment, setComment] = useState('')
  const [mode, setMode] = useState('reply')
  const [creative, setCreative] = useState(false)
  const [useLearned, setUseLearned] = useState(true)
  const [result, setResult] = useState<any>(null)
  const [learnedApplied, setLearnedApplied] = useState(false)

  const generate = trpc.draft.generate.useMutation({
    onSuccess: (data) => {
      if (data.error) {
        toast.error(data.error)
      } else {
        setResult(data.draft)
        setLearnedApplied(data.learnedApplied || false)
        toast.success(data.learnedApplied ? 'Draft generated with learned patterns' : 'Draft generated')
      }
    },
    onError: (err) => toast.error(err.message),
  })

  const handleGenerate = () => {
    if (!comment.trim()) { toast.error('Enter comment text'); return }
    if (!author.trim()) { toast.error('Enter author name'); return }
    setResult(null)
    setLearnedApplied(false)
    generate.mutate({
      comment: comment.trim(),
      author: author.trim(),
      location: location.trim() || null,
      mode: mode as any,
      creative,
      useLearned,
    })
  }

  const getStatusColor = (status: string) => {
    if (status === 'PASS') return 'text-emerald-400 border-emerald-800 bg-emerald-950'
    if (status === 'DEGRADE') return 'text-amber-400 border-amber-800 bg-amber-950'
    return 'text-red-400 border-red-800 bg-red-950'
  }

  const getRegimeColor = (regime: string) => {
    if (regime === 'CRYSTALLINE') return 'text-emerald-400'
    if (regime === 'FLUID') return 'text-blue-400'
    if (regime === 'GASEOUS') return 'text-amber-400'
    return 'text-red-400'
  }

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="mb-6">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <PenTool size={20} className="text-blue-400" />
          Draft Generator
        </h2>
        <p className="text-sm text-[#555] mt-1">Paste LinkedIn content, get VALO-gated reply</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input */}
        <Card className="bg-[#141414] border-[#222]">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Input</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-[#555]">Author Name</Label>
                <Input
                  value={author}
                  onChange={e => setAuthor(e.target.value)}
                  placeholder="e.g. Anders Hansen"
                  className="bg-[#1a1a1a] border-[#333] text-[#e8e8e8] text-sm mt-1"
                />
              </div>
              <div>
                <Label className="text-xs text-[#555]">Location</Label>
                <Input
                  value={location}
                  onChange={e => setLocation(e.target.value)}
                  placeholder="e.g. Oslo, Norway"
                  className="bg-[#1a1a1a] border-[#333] text-[#e8e8e8] text-sm mt-1"
                />
              </div>
            </div>

            <div>
              <Label className="text-xs text-[#555]">Mode</Label>
              <Select value={mode} onValueChange={setMode}>
                <SelectTrigger className="bg-[#1a1a1a] border-[#333] text-[#e8e8e8] text-sm mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#1a1a1a] border-[#333]">
                  <SelectItem value="reply">Reply to comment</SelectItem>
                  <SelectItem value="dm">Direct Message</SelectItem>
                  <SelectItem value="post">LinkedIn Post</SelectItem>
                  <SelectItem value="analyze">Profile Analysis</SelectItem>
                  <SelectItem value="redteam">Red Team Check</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="text-xs text-[#555]">Original Content</Label>
              <Textarea
                value={comment}
                onChange={e => setComment(e.target.value)}
                placeholder="Paste LinkedIn comment, message, or profile text here..."
                className="bg-[#1a1a1a] border-[#333] text-[#e8e8e8] text-sm mt-1 min-h-[120px]"
              />
            </div>

            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <Switch
                  checked={useLearned}
                  onCheckedChange={setUseLearned}
                  id="useLearned"
                />
                <Label htmlFor="useLearned" className="text-xs flex items-center gap-1">
                  <Brain size={12} className="text-purple-400" />
                  Apply Learned Patterns
                </Label>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Switch
                    checked={creative}
                    onCheckedChange={setCreative}
                    id="creative"
                  />
                  <Label htmlFor="creative" className="text-xs flex items-center gap-1">
                    <Sparkles size={12} className="text-purple-400" />
                    Creative Mode
                  </Label>
                </div>
                <Button
                  onClick={handleGenerate}
                  disabled={generate.isPending}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  {generate.isPending ? (
                    <Loader2 size={14} className="animate-spin mr-1" />
                  ) : (
                    <Zap size={14} className="mr-1" />
                  )}
                  Generate
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Output */}
        <Card className="bg-[#141414] border-[#222]">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Shield size={14} className="text-emerald-400" />
              VALO Output
            </CardTitle>
          </CardHeader>
          <CardContent>
            {result ? (
              <div className="space-y-4">
                {/* Gate Status */}
                <div className="flex items-center gap-3">
                  <Badge variant="outline" className={getStatusColor(result.combinedStatus)}>
                    {result.combinedStatus}
                  </Badge>
                  <span className={`text-xs font-bold ${getRegimeColor(result.tavRegime)}`}>
                    {result.tavRegime}
                  </span>
                  <span className="text-xs text-[#555]">τ={result.coherence}</span>
                  {result.mode === 'creative' && (
                    <Badge variant="outline" className="text-purple-400 border-purple-800 bg-purple-950 text-[10px]">
                      CREATIVE
                    </Badge>
                  )}
                  {learnedApplied && (
                    <Badge variant="outline" className="text-purple-400 border-purple-800 bg-purple-950 text-[10px] flex items-center gap-1">
                      <Brain size={10} /> LEARNED
                    </Badge>
                  )}
                </div>

                {/* VU Meter */}
                <div>
                  <div className="flex items-center gap-2 text-xs text-[#555] mb-1">
                    <span>VU Score</span>
                    <span className="text-[#e8e8e8] font-mono">{result.vuScore}/1000</span>
                  </div>
                  <div className="w-full h-2 bg-[#222] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.min(result.vuScore / 10, 100)}%`,
                        background: `linear-gradient(90deg, #ef4444 0%, #f59e0b 30%, #eab308 50%, #22c55e 80%, #16a34a 100%)`,
                      }}
                    />
                  </div>
                </div>

                <Separator className="bg-[#222]" />

                {/* Draft Text */}
                <div className="bg-[#1a1a1a] rounded-lg p-4 border border-[#333]">
                  <p className="text-sm text-[#e8e8e8] leading-relaxed whitespace-pre-wrap">
                    {result.text}
                  </p>
                </div>

                {/* Meta */}
                <div className="flex items-center gap-4 text-[10px] text-[#555]">
                  <span>Latency: {result.latencyMs}ms</span>
                  <span>Decision: {result.decision}</span>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-[#555]">
                <Shield size={32} className="mb-3 opacity-30" />
                <p className="text-sm">Generate a draft to see VALO analysis</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
