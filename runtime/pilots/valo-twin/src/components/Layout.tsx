import { Outlet, Link, useLocation } from 'react-router'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  LayoutDashboard,
  PenTool,
  ClipboardList,
  Eye,
  Brain,
  MonitorPlay,
  GraduationCap,
  Shield,
  Cpu,
} from 'lucide-react'

const navItems = [
  { icon: LayoutDashboard, label: 'Platform', path: '/' },
  { icon: MonitorPlay, label: 'Healthcare scenario', path: '/demo' },
  { icon: Cpu, label: 'Device execution', path: '/iot-ot-boundary' },
  { icon: GraduationCap, label: 'Ambassador onboarding', path: '/onboarding' },
  { icon: PenTool, label: 'Draft', path: '/draft' },
  { icon: ClipboardList, label: 'Queue', path: '/queue' },
  { icon: Eye, label: 'Watchlist', path: '/watchlist' },
  { icon: Brain, label: 'Learn', path: '/learn' },
]

export default function Layout() {
  const location = useLocation()

  return (
    <div className="flex h-screen w-full bg-[#0a0a0a] text-[#e8e8e8]">
      <aside className="flex w-60 flex-shrink-0 flex-col border-r border-[#222]">
        <div className="flex items-center gap-3 p-4">
          <div className="flex size-8 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-cyan-400 text-xs font-bold text-white">
            V
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-wide">VALO Twin</h1>
            <p className="text-[10px] text-[#666]">Execution Governance Platform</p>
          </div>
        </div>
        <Separator className="bg-[#222]" />
        <ScrollArea className="flex-1 py-2">
          <nav className="space-y-1 px-2">
            {navItems.map(item => {
              const isActive = location.pathname === item.path
              return (
                <Link key={item.path} to={item.path}>
                  <Button
                    variant="ghost"
                    className={`w-full justify-start gap-3 text-sm ${
                      isActive
                        ? 'bg-[#1a1a2e] text-blue-400 hover:bg-[#1a1a2e]'
                        : 'text-[#888] hover:bg-[#1a1a1a] hover:text-[#e8e8e8]'
                    }`}
                  >
                    <item.icon size={16} />
                    {item.label}
                  </Button>
                </Link>
              )
            })}
          </nav>
        </ScrollArea>
        <div className="border-t border-[#222] p-3">
          <div className="flex items-center gap-2 text-[10px] text-[#666]">
            <Shield size={12} className="text-emerald-500" />
            <span>Purpose → Receipt · governed</span>
          </div>
        </div>
      </aside>

      <main className="flex flex-1 flex-col overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}
