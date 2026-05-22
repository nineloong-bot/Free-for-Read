import { useState } from 'react'
import { EllipsisVertical, Trash2 } from 'lucide-react'
import type { Book } from '../api/client'
import { coverGradient } from '../lib/utils'

interface BookCardProps {
  book: Book
  index: number
  onClick: () => void
  selectMode: boolean
  selected: boolean
  onToggleSelect: () => void
  onDelete: () => void
}

export function BookCard({ book, index, onClick, selectMode, selected, onToggleSelect, onDelete }: BookCardProps) {
  const [menuOpen, setMenuOpen] = useState(false)

  const handleClick = () => {
    if (selectMode) {
      onToggleSelect()
    } else {
      onClick()
    }
  }

  const handleMenu = (e: React.MouseEvent) => {
    e.stopPropagation()
    setMenuOpen(o => !o)
  }

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    setMenuOpen(false)
    onDelete()
  }

  return (
    <div className="relative flex flex-col items-center" data-testid="book-card">
      {/* Select checkbox */}
      {selectMode && (
        <div className="absolute -top-2 -left-1 z-10" onClick={e => e.stopPropagation()}>
          <input type="checkbox" checked={selected} onChange={onToggleSelect}
            className="w-5 h-5 accent-[#d4641a] cursor-pointer" />
        </div>
      )}

      <div className="flex flex-col items-center cursor-pointer group" onClick={handleClick}>
        <div className="w-[120px] h-[160px] rounded-[10px] mb-2.5 shadow-md relative flex items-end p-2.5 transition-transform group-hover:scale-105"
          style={{ background: coverGradient(index) }}>
          {!selectMode && (
            <button onClick={handleMenu}
              className="absolute top-1 right-1 w-6 h-6 rounded-full bg-black/30 text-white opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
              <EllipsisVertical size={14} />
            </button>
          )}
          {/* Dropdown menu */}
          {menuOpen && !selectMode && (
            <div className="absolute top-7 right-1 bg-white rounded-lg shadow-lg border border-[#f0e8d9] py-1 z-20 min-w-[100px]">
              <button onClick={handleDelete}
                className="w-full text-left px-3 py-1.5 text-xs text-red-500 hover:bg-red-50 flex items-center gap-1.5">
                <Trash2 size={12} />删除
              </button>
            </div>
          )}
          {selected && (
            <div className="absolute inset-0 rounded-[10px] bg-[#d4641a]/20 border-2 border-[#d4641a] flex items-center justify-center">
              <div className="w-6 h-6 rounded-full bg-[#d4641a] text-white text-xs flex items-center justify-center">✓</div>
            </div>
          )}
        </div>
        <p className="text-[13px] font-semibold text-[#3d2e1c] text-center leading-tight max-w-[120px] truncate">{book.title}</p>
        <p className="text-[11px] text-[#b8a48e]">{book.author ?? '未知作者'}</p>
      </div>
    </div>
  )
}

export function ImportCard({ onClick }: { onClick: () => void }) {
  return (
    <div className="flex flex-col items-center cursor-pointer" onClick={onClick}>
      <div className="w-[120px] h-[160px] border-2 border-dashed border-[#e0d4c0] rounded-[10px] mb-2.5 flex items-center justify-center hover:border-[#d4641a] transition-colors">
        <div className="text-center text-[#c4b49a]">
          <p className="text-[28px] leading-none mb-1">+</p>
          <p className="text-[11px]">导入书籍</p>
        </div>
      </div>
    </div>
  )
}
