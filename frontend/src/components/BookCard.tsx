import type { Book } from '../api/client'
import { coverGradient } from '../lib/utils'

export function BookCard({ book, index, onClick }: { book: Book; index: number; onClick: () => void }) {
  return (
    <div className="flex flex-col items-center cursor-pointer group" onClick={onClick}>
      <div
        className="w-[120px] h-[160px] rounded-[10px] mb-2.5 shadow-md relative flex items-end p-2.5 transition-transform group-hover:scale-105"
        style={{ background: coverGradient(index) }}
      >
        <div className="absolute bottom-2 right-2 bg-black/50 text-white text-[9px] px-1.5 py-0.5 rounded">
          {book.chapter_count > 0 ? `${Math.round(book.word_count / (book.word_count + 1000) * 100)}%` : '0%'}
        </div>
      </div>
      <p className="text-[13px] font-semibold text-[#3d2e1c] text-center leading-tight">{book.title}</p>
      <p className="text-[11px] text-[#b8a48e]">{book.author ?? '未知作者'}</p>
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
