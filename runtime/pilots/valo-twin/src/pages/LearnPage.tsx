import { useState } from 'react'
import { trpc } from '@/providers/trpc'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { toast } from 'sonner'
import {
  Brain, Loader2, Plus, Sparkles, BookOpen, TrendingUp,
  MessageSquare, Trash2, Wand2, Lightbulb, Zap,
  ChevronDown, ChevronUp, Eye
} from 'lucide-react'

export default function LearnPage() {
  const utils = trpc.useUtils()
  const { data: stats } = trpc.learn.stats.useQuery()
  const { data: posts } = trpc.learn.posts.list.useQuery({})
  const { data: analyses } = trpc.learn.analyze.list.useQuery()
  const { data: patterns } = trpc.learn.patterns.list.useQuery({})
  const { data: voice } = trpc.learn.voice.list.useQuery({})
  const { data: promptEnhancement } = trpc.learn.promptEnhancement.useQuery()

  const [newPostContent, setNewPostContent] = useState('')
  const [newPostAuthor, setNewPostAuthor] = useState('')
  const [newPostMetrics, setNewPostMetrics] = useState('')
  const [expandedPost, setExpandedPost] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<'posts' | 'patterns' | 'voice' | 'insights'>('posts')

  const addPost = trpc.learn.posts.create.useMutation({
    onSuccess: () => {
      utils.learn.posts.list.invalidate()
      utils.learn.stats.invalidate()
      setNewPostContent('')
      setNewPostAuthor('')
      setNewPostMetrics('')
      toast.success('Reference post added')
    },
    onError: (err) => toast.error(err.message),
  })

  const analyzePost = trpc.learn.analyze.run.useMutation({
    onSuccess: (data) => {
      if (data.error) { toast.error(data.error); return }
      utils.learn.analyze.list.invalidate()
      utils.learn.posts.list.invalidate()
      utils.learn.stats.invalidate()
      toast.success('Post analyzed')
    },
    onError: (err) => toast.error(err.message),
  })

  const analyzeAll = trpc.learn.analyze.runAll.useMutation({
    onSuccess: (data) => {
      utils.learn.analyze.list.invalidate()
      utils.learn.posts.list.invalidate()
      utils.learn.stats.invalidate()
      toast.success(`Analyzed ${data.analyzed} posts`)
    },
    onError: (err) => toast.error(err.message),
  })

  const extractPatterns = trpc.learn.patterns.extract.useMutation({
    onSuccess: (data) => {
      if (data.error) { toast.error(data.error); return }
      utils.learn.patterns.list.invalidate()
      utils.learn.stats.invalidate()
      toast.success(`Extracted ${data.patterns.length} patterns`)
    },
    onError: (err) => toast.error(err.message),
  })

  const buildVoice = trpc.learn.voice.build.useMutation({
    onSuccess: (data) => {
      if (data.error) { toast.error(data.error); return }
      utils.learn.voice.list.invalidate()
      utils.learn.stats.invalidate()
      toast.success(`Built voice profile with ${data.entries.length} entries`)
    },
    onError: (err) => toast.error(err.message),
  })

  const deletePost = trpc.learn.posts.delete.useMutation({
    onSuccess: () => {
      utils.learn.posts.list.invalidate()
      utils.learn.stats.invalidate()
      toast.success('Post removed')
    },
  })

  const deletePattern = trpc.learn.patterns.delete.useMutation({
    onSuccess: () => {
      utils.learn.patterns.list.invalidate()
      utils.learn.stats.invalidate()
      toast.success('Pattern removed')
    },
  })

  const deleteVoiceEntry = trpc.learn.voice.delete.useMutation({
    onSuccess: () => {
      utils.learn.voice.list.invalidate()
      utils.learn.stats.invalidate()
      toast.success('Voice entry removed')
    },
  })

  const parseMetrics = (s: string) => {
    try {
      return JSON.parse(s)
    } catch {
      return undefined
    }
  }

  const getPatternColor = (type: string) => {
    switch (type) {
      case 'hook': return 'text-emerald-400 border-emerald-800 bg-emerald-950'
      case 'structure': return 'text-blue-400 border-blue-800 bg-blue-950'
      case 'tone': return 'text-purple-400 border-purple-800 bg-purple-950'
      case 'voice': return 'text-amber-400 border-amber-800 bg-amber-950'
      case 'topic_angle': return 'text-cyan-400 border-cyan-800 bg-cyan-950'
      case 'engagement': return 'text-pink-400 border-pink-800 bg-pink-950'
      default: return 'text-gray-400 border-gray-800 bg-gray-950'
    }
  }

  const getVoiceColor = (cat: string) => {
    switch (cat) {
      case 'phrasing': return 'text-emerald-400'
      case 'strong_opinion': return 'text-blue-400'
      case 'pet_peeve': return 'text-red-400'
      case 'banned_word': return 'text-red-400'
      case 'signature_move': return 'text-purple-400'
      case 'preference': return 'text-amber-400'
      default: return 'text-gray-400'
    }
  }

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="mb-6">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Brain size={20} className="text-purple-400" />
          VALO Learn Engine
        </h2>
        <p className="text-sm text-[#555] mt-1">Self-learning AI — analyzes what works, replicates success</p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
        {[
          { label: 'Reference Posts', value: stats?.totalPosts || 0, icon: BookOpen, color: 'bg-blue-600' },
          { label: 'Analyzed', value: stats?.analyzedPosts || 0, icon: Eye, color: 'bg-emerald-600' },
          { label: 'Patterns', value: stats?.totalPatterns || 0, icon: Sparkles, color: 'bg-purple-600' },
          { label: 'Voice Entries', value: stats?.voiceEntries || 0, icon: MessageSquare, color: 'bg-amber-600' },
          { label: 'Feedback', value: stats?.feedbackEntries || 0, icon: TrendingUp, color: 'bg-cyan-600' },
        ].map(({ label, value, icon: Icon, color }) => (
          <Card key={label} className="bg-[#141414] border-[#222]">
            <CardContent className="p-3 flex items-center gap-3">
              <div className={`p-2 rounded-lg ${color}`}>
                <Icon size={16} className="text-white" />
              </div>
              <div>
                <p className="text-lg font-bold text-[#e8e8e8]">{value}</p>
                <p className="text-[10px] text-[#555]">{label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Prompt Enhancement Preview */}
      {promptEnhancement?.hasLearnings && (
        <Card className="bg-[#141414] border-[#222] mb-6">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Zap size={14} className="text-yellow-400" />
              Active Learning Context
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-[#555] mb-2">Currently injected into every draft generation:</p>
            <pre className="bg-[#1a1a1a] rounded p-3 border border-[#333] text-xs text-[#888] whitespace-pre-wrap max-h-40 overflow-auto font-mono">
              {promptEnhancement.enhancement}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* Action Bar */}
      <div className="flex flex-wrap gap-2 mb-6">
        <Button
          size="sm"
          variant="outline"
          className="border-purple-800 text-purple-400 hover:bg-purple-950"
          onClick={() => analyzeAll.mutate()}
          disabled={analyzeAll.isPending}
        >
          {analyzeAll.isPending ? <Loader2 size={12} className="animate-spin mr-1" /> : <Wand2 size={12} className="mr-1" />}
          Analyze All Unanalyzed
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="border-emerald-800 text-emerald-400 hover:bg-emerald-950"
          onClick={() => extractPatterns.mutate()}
          disabled={extractPatterns.isPending}
        >
          {extractPatterns.isPending ? <Loader2 size={12} className="animate-spin mr-1" /> : <Sparkles size={12} className="mr-1" />}
          Extract Patterns
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="border-amber-800 text-amber-400 hover:bg-amber-950"
          onClick={() => buildVoice.mutate()}
          disabled={buildVoice.isPending}
        >
          {buildVoice.isPending ? <Loader2 size={12} className="animate-spin mr-1" /> : <Brain size={12} className="mr-1" />}
          Build Voice Profile
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-4 border-b border-[#222]">
        {(['posts', 'patterns', 'voice', 'insights'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? 'border-purple-400 text-purple-400'
                : 'border-transparent text-[#555] hover:text-[#888]'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Posts Tab */}
      {activeTab === 'posts' && (
        <div className="space-y-4">
          {/* Add Post Form */}
          <Card className="bg-[#141414] border-[#222]">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Plus size={14} />
                Add Reference Post
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input
                placeholder="Author name (optional)"
                value={newPostAuthor}
                onChange={(e) => setNewPostAuthor(e.target.value)}
                className="bg-[#1a1a1a] border-[#333] text-[#e8e8e8] text-sm"
              />
              <Textarea
                placeholder="Paste LinkedIn post content here..."
                value={newPostContent}
                onChange={(e) => setNewPostContent(e.target.value)}
                className="bg-[#1a1a1a] border-[#333] text-[#e8e8e8] text-sm min-h-[100px]"
              />
              <Input
                placeholder='Metrics JSON: {"likes":150,"comments":25,"shares":10}'
                value={newPostMetrics}
                onChange={(e) => setNewPostMetrics(e.target.value)}
                className="bg-[#1a1a1a] border-[#333] text-[#e8e8e8] text-sm"
              />
              <Button
                size="sm"
                className="bg-purple-600 hover:bg-purple-700"
                onClick={() => {
                  if (!newPostContent.trim()) { toast.error('Enter post content'); return }
                  addPost.mutate({
                    content: newPostContent.trim(),
                    authorName: newPostAuthor.trim() || undefined,
                    metrics: newPostMetrics.trim() ? parseMetrics(newPostMetrics) : undefined,
                  })
                }}
                disabled={addPost.isPending}
              >
                {addPost.isPending ? <Loader2 size={12} className="animate-spin mr-1" /> : <Plus size={12} className="mr-1" />}
                Add & Analyze
              </Button>
            </CardContent>
          </Card>

          {/* Posts List */}
          {posts && posts.length > 0 ? (
            <div className="space-y-2">
              {posts.map((post) => (
                <Card key={post.id} className="bg-[#141414] border-[#222]">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="outline" className="text-[10px]">
                            {post.source}
                          </Badge>
                          {post.topic && (
                            <Badge variant="outline" className="text-[10px] text-purple-400 border-purple-800">
                              {post.topic}
                            </Badge>
                          )}
                          {post.analyzedAt ? (
                            <Badge variant="outline" className="text-[10px] text-emerald-400 border-emerald-800">
                              Analyzed
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="text-[10px] text-amber-400 border-amber-800">
                              Pending
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-[#e8e8e8] line-clamp-2">{post.content}</p>
                        {(() => {
                          const m = post.metrics as Record<string, number> | null;
                          if (!m) return null;
                          return (
                            <div className="flex gap-3 mt-1 text-[10px] text-[#555]">
                              <span>{m.likes || 0} likes</span>
                              <span>{m.comments || 0} comments</span>
                              <span>{m.shares || 0} shares</span>
                            </div>
                          );
                        })()}
                      </div>
                      <div className="flex items-center gap-1 ml-2">
                        {!post.analyzedAt && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 w-7 p-0 text-purple-400 hover:text-purple-300"
                            onClick={() => analyzePost.mutate({ postId: post.id })}
                            disabled={analyzePost.isPending}
                          >
                            <Wand2 size={14} />
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 w-7 p-0 text-[#555] hover:text-red-400"
                          onClick={() => deletePost.mutate({ id: post.id })}
                        >
                          <Trash2 size={14} />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 w-7 p-0 text-[#555]"
                          onClick={() => setExpandedPost(expandedPost === post.id ? null : post.id)}
                        >
                          {expandedPost === post.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </Button>
                      </div>
                    </div>

                    {/* Expanded Analysis */}
                    {expandedPost === post.id && (
                      <div className="mt-3 pt-3 border-t border-[#222]">
                        <PostAnalysisView postId={post.id} />
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="bg-[#141414] border-[#222]">
              <CardContent className="p-12 text-center">
                <BookOpen size={32} className="mx-auto mb-3 text-[#333]" />
                <p className="text-sm text-[#555]">No reference posts yet</p>
                <p className="text-xs text-[#555] mt-1">Add high-performing LinkedIn posts above to start learning</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Patterns Tab */}
      {activeTab === 'patterns' && (
        <div className="space-y-3">
          {patterns && patterns.length > 0 ? (
            patterns.map((p) => (
              <Card key={p.id} className="bg-[#141414] border-[#222]">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="outline" className={`text-[10px] ${getPatternColor(p.patternType || '')}`}>
                          {p.patternType}
                        </Badge>
                        <span className="text-[10px] text-[#555]">confidence: {Math.round((p.confidence || 0) * 100)}%</span>
                        <span className="text-[10px] text-[#555]">used: {p.usageCount || 0}x</span>
                      </div>
                      <p className="text-sm text-[#e8e8e8]">{p.pattern}</p>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 w-7 p-0 text-[#555] hover:text-red-400 ml-2"
                      onClick={() => deletePattern.mutate({ id: p.id })}
                    >
                      <Trash2 size={14} />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))
          ) : (
            <Card className="bg-[#141414] border-[#222]">
              <CardContent className="p-12 text-center">
                <Sparkles size={32} className="mx-auto mb-3 text-[#333]" />
                <p className="text-sm text-[#555]">No patterns extracted yet</p>
                <p className="text-xs text-[#555] mt-1">Analyze posts first, then click &quot;Extract Patterns&quot; to find recurring success factors</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Voice Tab */}
      {activeTab === 'voice' && (
        <div className="space-y-3">
          {voice && voice.length > 0 ? (
            voice.map((v) => (
              <Card key={v.id} className="bg-[#141414] border-[#222]">
                <CardContent className="p-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-medium ${getVoiceColor(v.category || '')}`}>
                          {v.category}
                        </span>
                        <span className="text-[10px] text-[#555]">{v.source}</span>
                        <span className="text-[10px] text-[#555]">{Math.round((v.confidence || 0) * 100)}%</span>
                      </div>
                      <p className="text-sm text-[#e8e8e8]">{v.content}</p>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 w-7 p-0 text-[#555] hover:text-red-400 ml-2"
                      onClick={() => deleteVoiceEntry.mutate({ id: v.id })}
                    >
                      <Trash2 size={14} />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))
          ) : (
            <Card className="bg-[#141414] border-[#222]">
              <CardContent className="p-12 text-center">
                <Brain size={32} className="mx-auto mb-3 text-[#333]" />
                <p className="text-sm text-[#555]">No voice profile entries yet</p>
                <p className="text-xs text-[#555] mt-1">Click &quot;Build Voice Profile&quot; after analyzing posts to auto-generate voice entries</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Insights Tab */}
      {activeTab === 'insights' && (
        <div className="space-y-4">
          {/* Analysis Summary */}
          <Card className="bg-[#141414] border-[#222]">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Lightbulb size={14} className="text-amber-400" />
                Post Analysis Insights
              </CardTitle>
            </CardHeader>
            <CardContent>
              {analyses && analyses.length > 0 ? (
                <div className="space-y-3">
                  {/* Hook Types Distribution */}
                  <div>
                    <p className="text-xs text-[#555] mb-2">Hook Types</p>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(
                        analyses.reduce((acc, a) => {
                          const key = a.hookType || 'unknown'
                          acc[key] = (acc[key] || 0) + 1
                          return acc
                        }, {} as Record<string, number>)
                      ).map(([hook, count]) => (
                        <Badge key={hook} variant="outline" className="text-xs text-emerald-400 border-emerald-800">
                          {hook}: {count}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <Separator className="bg-[#222]" />
                  {/* Structure Types */}
                  <div>
                    <p className="text-xs text-[#555] mb-2">Structures</p>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(
                        analyses.reduce((acc, a) => {
                          const key = a.structureType || 'unknown'
                          acc[key] = (acc[key] || 0) + 1
                          return acc
                        }, {} as Record<string, number>)
                      ).map(([struct, count]) => (
                        <Badge key={struct} variant="outline" className="text-xs text-blue-400 border-blue-800">
                          {struct}: {count}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <Separator className="bg-[#222]" />
                  {/* Tones */}
                  <div>
                    <p className="text-xs text-[#555] mb-2">Emotional Tones</p>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(
                        analyses.reduce((acc, a) => {
                          const key = a.emotionalTone || 'unknown'
                          acc[key] = (acc[key] || 0) + 1
                          return acc
                        }, {} as Record<string, number>)
                      ).map(([tone, count]) => (
                        <Badge key={tone} variant="outline" className="text-xs text-purple-400 border-purple-800">
                          {tone}: {count}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-[#555]">No analyses yet. Analyze posts to see insights.</p>
              )}
            </CardContent>
          </Card>

          {/* Key Insights */}
          {analyses && analyses.length > 0 && (
            <Card className="bg-[#141414] border-[#222]">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <MessageSquare size={14} className="text-blue-400" />
                  Key Insights from Analyses
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {analyses
                    .filter((a) => a.keyInsights)
                    .sort((a, b) => (b.score || 0) - (a.score || 0))
                    .slice(0, 10)
                    .map((a, i) => (
                      <div key={a.id} className="flex gap-2 text-xs">
                        <span className="text-[#555] shrink-0">{i + 1}.</span>
                        <p className="text-[#888]">{a.keyInsights}</p>
                      </div>
                    ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}

// Sub-component for viewing post analysis
function PostAnalysisView({ postId }: { postId: number }) {
  const { data: analysis, isLoading } = trpc.learn.analyze.forPost.useQuery({ postId })

  if (isLoading) return <div className="flex justify-center py-4"><Loader2 className="animate-spin text-purple-400" size={16} /></div>
  if (!analysis) return <p className="text-xs text-[#555]">No analysis available</p>

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-[#1a1a1a] rounded p-2 border border-[#333]">
          <p className="text-[10px] text-[#555]">Hook</p>
          <p className="text-xs text-emerald-400">{analysis.hookType}</p>
        </div>
        <div className="bg-[#1a1a1a] rounded p-2 border border-[#333]">
          <p className="text-[10px] text-[#555]">Structure</p>
          <p className="text-xs text-blue-400">{analysis.structureType}</p>
        </div>
        <div className="bg-[#1a1a1a] rounded p-2 border border-[#333]">
          <p className="text-[10px] text-[#555]">Tone</p>
          <p className="text-xs text-purple-400">{analysis.emotionalTone}</p>
        </div>
      </div>
      <div className="bg-[#1a1a1a] rounded p-2 border border-[#333]">
        <p className="text-[10px] text-[#555] mb-1">Score: {Math.round((analysis.score || 0) * 100)}%</p>
        <div className="w-full h-1.5 bg-[#222] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-yellow-500 to-emerald-500"
            style={{ width: `${(analysis.score || 0) * 100}%` }}
          />
        </div>
      </div>
      {(() => {
        const factors = analysis.successFactors as string[] | null;
        if (!factors || factors.length === 0) return null;
        return (
          <div>
            <p className="text-[10px] text-[#555] mb-1">Success Factors</p>
            <div className="flex flex-wrap gap-1">
              {factors.map((factor, i) => (
                <Badge key={i} variant="outline" className="text-[10px] text-amber-400 border-amber-800">
                  {factor}
                </Badge>
              ))}
            </div>
          </div>
        );
      })()}
      {analysis.keyInsights && (
        <p className="text-xs text-[#888] italic">{analysis.keyInsights}</p>
      )}
    </div>
  )
}