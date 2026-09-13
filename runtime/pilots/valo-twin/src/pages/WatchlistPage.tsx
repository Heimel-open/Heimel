import { useState } from 'react'
import { trpc } from '@/providers/trpc'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { Eye, Plus, Loader2 } from 'lucide-react'

export default function WatchlistPage() {
  const [name, setName] = useState('')
  const [company, setCompany] = useState('')
  const [linkedinUrl, setLinkedinUrl] = useState('')
  const [notes, setNotes] = useState('')

  const utils = trpc.useUtils()
  const { data: items, isLoading } = trpc.watchlist.list.useQuery()

  const add = trpc.watchlist.add.useMutation({
    onSuccess: () => {
      utils.watchlist.list.invalidate()
      setName(''); setCompany(''); setLinkedinUrl(''); setNotes('')
      toast.success('Added to watchlist')
    },
    onError: (err) => toast.error(err.message),
  })

  const updateFlag = trpc.watchlist.updateFlag.useMutation({
    onSuccess: () => { utils.watchlist.list.invalidate(); toast.success('Flag updated') },
  })

  const getFlagColor = (flag: string) => {
    switch (flag) {
      case 'monitor': return 'text-amber-400 border-amber-800 bg-amber-950'
      case 'engage': return 'text-emerald-400 border-emerald-800 bg-emerald-950'
      case 'avoid': return 'text-red-400 border-red-800 bg-red-950'
      case 'critical': return 'text-purple-400 border-purple-800 bg-purple-950'
      default: return ''
    }
  }

  const flags = ['monitor', 'engage', 'avoid', 'critical']

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="mb-6">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Eye size={20} className="text-blue-400" />
          Watchlist
        </h2>
        <p className="text-sm text-[#555] mt-1">Tracked contacts and opportunities</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Add Form */}
        <Card className="bg-[#141414] border-[#222] lg:col-span-1">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Plus size={14} />
              Add Contact
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <Label className="text-xs text-[#555]">Name *</Label>
              <Input value={name} onChange={e => setName(e.target.value)} placeholder="Full name" className="bg-[#1a1a1a] border-[#333] text-[#e8e8e8] text-sm mt-1" />
            </div>
            <div>
              <Label className="text-xs text-[#555]">Company</Label>
              <Input value={company} onChange={e => setCompany(e.target.value)} placeholder="Company name" className="bg-[#1a1a1a] border-[#333] text-[#e8e8e8] text-sm mt-1" />
            </div>
            <div>
              <Label className="text-xs text-[#555]">LinkedIn URL</Label>
              <Input value={linkedinUrl} onChange={e => setLinkedinUrl(e.target.value)} placeholder="https://linkedin.com/in/..." className="bg-[#1a1a1a] border-[#333] text-[#e8e8e8] text-sm mt-1" />
            </div>
            <div>
              <Label className="text-xs text-[#555]">Notes</Label>
              <Input value={notes} onChange={e => setNotes(e.target.value)} placeholder="Why track this person?" className="bg-[#1a1a1a] border-[#333] text-[#e8e8e8] text-sm mt-1" />
            </div>
            <Button
              className="w-full bg-blue-600 hover:bg-blue-700"
              onClick={() => {
                if (!name.trim()) { toast.error('Name required'); return }
                add.mutate({
                  name: name.trim(),
                  company: company.trim() || undefined,
                  linkedinUrl: linkedinUrl.trim() || undefined,
                  notes: notes.trim() || undefined,
                })
              }}
              disabled={add.isPending}
            >
              {add.isPending ? <Loader2 size={14} className="animate-spin mr-1" /> : <Plus size={14} className="mr-1" />}
              Add to Watchlist
            </Button>
          </CardContent>
        </Card>

        {/* List */}
        <div className="lg:col-span-2 space-y-3">
          {isLoading ? (
            <div className="flex justify-center py-12"><Loader2 className="animate-spin text-blue-400" /></div>
          ) : items && items.length > 0 ? (
            items.map(item => (
              <Card key={item.id} className="bg-[#141414] border-[#222]">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-sm font-semibold text-[#e8e8e8]">{item.name}</h3>
                        <Badge variant="outline" className={getFlagColor(item.flag || 'monitor')}>
                          {item.flag || 'monitor'}
                        </Badge>
                      </div>
                      {item.company && <p className="text-xs text-[#888]">{item.company}</p>}
                      {item.linkedinUrl && (
                        <a href={item.linkedinUrl} target="_blank" rel="noopener" className="text-xs text-blue-400 hover:underline">
                          View Profile
                        </a>
                      )}
                      {item.notes && <p className="text-xs text-[#555] mt-2 italic">{item.notes}</p>}
                    </div>
                    <div className="flex flex-col gap-1">
                      {flags.map(f => (
                        <Button
                          key={f}
                          size="sm"
                          variant={item.flag === f ? "default" : "ghost"}
                          className={`text-[10px] h-6 px-2 ${item.flag === f ? 'bg-[#222] text-[#e8e8e8]' : 'text-[#555] hover:text-[#888]'}`}
                          onClick={() => updateFlag.mutate({ id: item.id, flag: f as any })}
                        >
                          {f}
                        </Button>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          ) : (
            <Card className="bg-[#141414] border-[#222]">
              <CardContent className="p-12 text-center">
                <Eye size={32} className="mx-auto mb-3 text-[#333]" />
                <p className="text-sm text-[#555]">Watchlist is empty</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
