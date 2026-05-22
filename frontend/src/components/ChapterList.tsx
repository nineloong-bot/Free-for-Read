import { useState } from 'react'
import { Bookmark, X } from 'lucide-react'
import type { ChapterSummary } from '../api/client'

interface Props {
  chapters: ChapterSummary[]
  currentIndex: number
  bookmarkedIds: Set<string>
  onSelect: (index: number) => void
  onClose: () => void
}

export function ChapterList({ chapters, currentIndex, bookmarkedIds, onSelect, onClose }: Props) {
  const [filter, setFilter] = useState<'all' | 'bookmarks'>('all')

  const list = filter === 'bookmarks'
    ? chapters.filter(ch => bookmarkedIds.has(ch.id))
    : chapters

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/20" onClick={onClose}>
      <div className="bg-white rounded-t-2xl w-full max-w-md max-h-[70vh] flex flex-col shadow-xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-3 border-b border-[#f0e8d9] shrink-0">
          <span className="text-sm font-semibold text-[#3d2e1c]">目录 ({chapters.length} 章)</span>
          <button onClick={onClose} className="w-7 h-7 rounded-full flex items-center justify-center"><X size={16} color="#888" /></button>
        </div>
        {/* Filter tabs */}
        <div className="flex bg-[#faf7f2] border-b border-[#f0e8d9] px-2 py-1 gap-1 shrink-0">
          <button onClick={() => setFilter('all')}
            className={`px-3 py-1 text-xs rounded-md ${filter === 'all' ? 'bg-white text-[#d4641a] font-semibold shadow-sm' : 'text-[#b8a48e]'}`}>全部</button>
          <button onClick={() => setFilter('bookmarks')}
            className={`px-3 py-1 text-xs rounded-md flex items-center gap-1 ${filter === 'bookmarks' ? 'bg-white text-[#d4641a] font-semibold shadow-sm' : 'text-[#b8a48e]'}`}>
            <Bookmark size={10} fill={filter === 'bookmarks' ? '#d4641a' : '#b8a48e'} />
            收藏 {bookmarkedIds.size > 0 && `(${bookmarkedIds.size})`}
          </button>
        </div>
        <div className="flex-1 overflow-auto">
          {list.length === 0 ? (
            <p className="text-center text-sm text-[#b8a48e] py-12">暂无收藏章节</p>
          ) : list.map(ch => {
            const origIdx = chapters.findIndex(c => c.id === ch.id)
            return (
              <button
                key={ch.id}
                onClick={() => { onSelect(origIdx); onClose() }}
                className={`w-full text-left px-5 py-3 text-sm border-b border-[#f5efe0] hover:bg-[#faf7f2] flex items-center ${origIdx === currentIndex ? 'text-[#d4641a] font-semibold bg-[#fef7f0]' : 'text-[#3d2e1c]'}`}
              >
                <span className="text-xs text-[#b8a48e] mr-2">{origIdx + 1}.</span>
                <span className="flex-1">{ch.title || `第 ${origIdx + 1} 章`}</span>
                {bookmarkedIds.has(ch.id) && (
                  <Bookmark size={12} fill="#d4641a" stroke="#d4641a" />
                )}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
