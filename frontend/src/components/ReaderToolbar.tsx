import { ChevronLeft, ChevronRight, Bookmark, Type } from 'lucide-react'
import type { ThemeId } from './ReadingSettings'

const themeDots: Record<ThemeId, string> = { default: '#fefcf5', eyecare: '#f5ecd7', night: '#1a1a1a', parchment: '#e8dcc8' }

interface Props {
  chapterIndex: number; chapterCount: number
  onPrevChapter: () => void; onNextChapter: () => void
  currentTheme: ThemeId; onSettingsToggle: () => void
  isBookmarked: boolean; onBookmarkToggle: () => void
}

export function ReaderToolbar(props: Props) {
  const hasPrev = props.chapterIndex > 0 || props.chapterCount > 1
  const hasNext = props.chapterIndex < props.chapterCount - 1
  return (
    <div className="bg-white border-t border-[#f0e8d9] px-5 py-2 flex items-center justify-between max-w-[640px] mx-auto rounded-t-xl shadow-[0_-2px_12px_rgba(0,0,0,0.04)]" data-testid="reader-toolbar">
      <div className="flex items-center gap-4">
        <button onClick={props.onPrevChapter} disabled={!hasPrev} className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg border border-[#f0e8d9] text-[13px] text-[#3d2e1c] hover:bg-[#faf7f2] ${!hasPrev ? 'opacity-30 cursor-default' : ''}`}><ChevronLeft size={14} />上一章</button>
        <span className="text-[13px] text-[#b8a48e]"><span className="text-[#d4641a] font-semibold">{props.chapterIndex + 1}</span> / {props.chapterCount}</span>
        <button onClick={props.onNextChapter} disabled={!hasNext} className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg border border-[#f0e8d9] text-[13px] text-[#3d2e1c] hover:bg-[#faf7f2] ${!hasNext ? 'opacity-30 cursor-default' : ''}`}>下一章<ChevronRight size={14} /></button>
      </div>
      <div className="flex items-center gap-2">
        <button onClick={props.onBookmarkToggle} className={`w-9 h-9 rounded-lg border flex items-center justify-center ${props.isBookmarked ? 'border-[#d4641a] bg-[#fef7f0]' : 'border-[#f0e8d9] bg-white'}`}>
          <Bookmark size={16} fill={props.isBookmarked ? '#d4641a' : 'none'} stroke={props.isBookmarked ? '#d4641a' : '#888'} />
        </button>
        <button onClick={props.onSettingsToggle} className="w-9 h-9 rounded-lg border border-[#f0e8d9] bg-white flex items-center justify-center"><Type size={16} stroke="#888" /></button>
        <div className="flex gap-1 ml-1">
          {Object.entries(themeDots).map(([id, c]) => (
            <div key={id} className={`w-5 h-5 rounded-full border-2 ${props.currentTheme === id ? 'border-[#d4641a]' : 'border-transparent'}`} style={{ backgroundColor: c }} />
          ))}
        </div>
      </div>
    </div>
  )
}
