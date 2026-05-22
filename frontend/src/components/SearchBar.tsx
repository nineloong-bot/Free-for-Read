import { useState, useEffect, useRef } from 'react'
import { Loader2, Search } from 'lucide-react'
import { searchBooks } from '../api/client'

interface SearchResult {
  book_id: string; book_title: string; chapter_id: string
  chapter_title: string; text: string; score: number
}

export function SearchBar() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    setResults([])
    try {
      const data = await searchBooks(query.trim())
      setResults(data.results)
      setOpen(true)
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div ref={containerRef} className="relative" data-testid="search-bar">
      <div className="flex gap-2">
        <div className="flex-1 relative">
          <Search size={16} stroke="#b8a48e" className="absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            value={query} onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="搜索所有书籍中的内容..."
            className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[#f0e8d9] bg-white focus:outline-none focus:border-[#d4641a]"
          />
        </div>
        <button onClick={handleSearch} disabled={loading}
          className="px-4 py-2 bg-[#d4641a] text-white rounded-lg text-xs font-semibold disabled:opacity-60 flex items-center gap-1.5">
          {loading && <Loader2 size={12} className="animate-spin" />}
          搜索
        </button>
      </div>
      {open && results.length > 0 && (
        <div className="absolute top-full mt-2 left-0 right-0 bg-white rounded-xl border border-[#f0e8d9] shadow-lg z-30 max-h-[300px] overflow-auto">
          {results.map((r, i) => (
            <div key={i} className="p-3 border-b border-[#f0e8d9] last:border-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-semibold text-[#3d2e1c]">
                  {r.book_title} · {r.chapter_title}
                </span>
                <span className="text-[10px] text-[#d4641a] bg-[#fef7f0] px-1.5 py-0.5 rounded">
                  {Math.round(r.score * 100)}%
                </span>
              </div>
              <p className="text-xs text-[#4a3f30] leading-relaxed line-clamp-2">{r.text}</p>
            </div>
          ))}
        </div>
      )}
      {open && results.length === 0 && !loading && (
        <div className="absolute top-full mt-2 left-0 right-0 bg-white rounded-xl border border-[#f0e8d9] shadow-lg z-30 p-4 text-center text-xs text-[#b8a48e]">
          未找到相关内容
        </div>
      )}
    </div>
  )
}
