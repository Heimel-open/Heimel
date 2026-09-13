import { trpc } from '@/providers/trpc'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { ClipboardList, CheckCircle, XCircle, Send, Loader2 } from 'lucide-react'

export default function QueuePage() {
  const utils = trpc.useUtils()
  const { data: items, isLoading } = trpc.queue.list.useQuery({})

  const approve = trpc.queue.approve.useMutation({
    onSuccess: () => { utils.queue.list.invalidate(); toast.success('Approved') },
  })
  const reject = trpc.queue.reject.useMutation({
    onSuccess: () => { utils.queue.list.invalidate(); toast.success('Rejected') },
  })
  const post = trpc.queue.post.useMutation({
    onSuccess: () => { utils.queue.list.invalidate(); toast.success('Marked as posted') },
  })

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending': return <Badge variant="outline" className="text-amber-400 border-amber-800 bg-amber-950">PENDING</Badge>
      case 'approved': return <Badge variant="outline" className="text-emerald-400 border-emerald-800 bg-emerald-950">APPROVED</Badge>
      case 'rejected': return <Badge variant="outline" className="text-red-400 border-red-800 bg-red-950">REJECTED</Badge>
      case 'posted': return <Badge variant="outline" className="text-blue-400 border-blue-800 bg-blue-950">POSTED</Badge>
      default: return <Badge variant="outline">{status}</Badge>
    }
  }

  const getStatusColor = (status: string) => {
    if (status === 'PASS') return 'text-emerald-400'
    if (status === 'DEGRADE') return 'text-amber-400'
    return 'text-red-400'
  }

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="mb-6">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <ClipboardList size={20} className="text-blue-400" />
          Approval Queue
        </h2>
        <p className="text-sm text-[#555] mt-1">{items?.length || 0} drafts waiting for review</p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Loader2 className="animate-spin text-blue-400" /></div>
      ) : items && items.length > 0 ? (
        <div className="space-y-3">
          {items.map((item) => (
            <Card key={item.id} className="bg-[#141414] border-[#222]">
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3 flex-wrap">
                    {getStatusBadge(item.status || 'pending')}
                    <Badge variant="outline" className={`${getStatusColor(item.combinedStatus || 'HALT')} text-[10px]`}>
                      {item.combinedStatus}
                    </Badge>
                    <span className="text-xs text-[#555]">{item.tavRegime}</span>
                    <span className="text-xs text-[#555]">τ={item.coherence}</span>
                  </div>
                  <span className="text-[10px] text-[#555]">
                    {item.createdAt ? new Date(item.createdAt).toLocaleDateString() : ''}
                  </span>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-3">
                  <div className="bg-[#1a1a1a] rounded p-3 border border-[#333]">
                    <p className="text-[10px] text-[#555] mb-1">ORIGINAL</p>
                    <p className="text-xs text-[#888] line-clamp-3">{item.original || ''}</p>
                  </div>
                  <div className="bg-[#1a1a1a] rounded p-3 border border-[#333]">
                    <p className="text-[10px] text-[#555] mb-1">DRAFT</p>
                    <p className="text-xs text-[#e8e8e8] line-clamp-3">{item.draft || ''}</p>
                  </div>
                </div>

                {item.status === 'pending' && (
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-emerald-800 text-emerald-400 hover:bg-emerald-950"
                      onClick={() => approve.mutate({ id: item.id })}
                      disabled={approve.isPending}
                    >
                      <CheckCircle size={12} className="mr-1" /> Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-red-800 text-red-400 hover:bg-red-950"
                      onClick={() => reject.mutate({ id: item.id })}
                      disabled={reject.isPending}
                    >
                      <XCircle size={12} className="mr-1" /> Reject
                    </Button>
                  </div>
                )}

                {item.status === 'approved' && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-blue-800 text-blue-400 hover:bg-blue-950"
                    onClick={() => post.mutate({ id: item.id })}
                    disabled={post.isPending}
                  >
                    <Send size={12} className="mr-1" /> Mark Posted
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="bg-[#141414] border-[#222]">
          <CardContent className="p-12 text-center">
            <ClipboardList size={32} className="mx-auto mb-3 text-[#333]" />
            <p className="text-sm text-[#555]">No drafts in queue</p>
            <p className="text-xs text-[#555] mt-1">Generate drafts from the Draft page</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
