import { BookOpen, FileText, Sparkles, Settings } from 'lucide-react'
import type { View } from '../contexts/AppContext'

const tabs = [
  { id: 'library' as const, label: '书架', icon: BookOpen },
  { id: 'parser' as const, label: '解析', icon: FileText },
  { id: 'ai' as const, label: 'AI', icon: Sparkles },
  { id: 'settings' as const, label: '设置', icon: Settings },
]

export function BottomNav({ activeView, onNavigate }: { activeView: View; onNavigate: (v: View) => void }) {
  return (
    <nav className="h-14 bg-white border-t border-[#f0e8d9] flex items-center justify-around px-5">
      {tabs.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          onClick={() => onNavigate(id)}
          className={`flex flex-col items-center gap-0.5 ${
            activeView === id ? 'text-[#d4641a]' : 'text-[#b8a48e]'
          }`}
        >
          <Icon size={20} strokeWidth={2} />
          <span className="text-[10px] font-semibold">{label}</span>
        </button>
      ))}
    </nav>
  )
}
