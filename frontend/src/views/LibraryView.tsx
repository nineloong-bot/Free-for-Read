import { useEffect, useState } from 'react'
import { Search, Plus } from 'lucide-react'
import { listBooks, importBook, type Book } from '../api/client'
import { BookCard, ImportCard } from '../components/BookCard'
import { useApp } from '../contexts/AppContext'

export function LibraryView() {
  const { selectBook, ready } = useApp()
  const [books, setBooks] = useState<Book[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retries, setRetries] = useState(0)

  const refresh = async () => {
    try { setLoading(true); setError(null); const data = await listBooks(); setBooks(data.items) }
    catch (e) { setError((e as Error).message); console.error('Failed to load books', e) }
    finally { setLoading(false) }
  }

  useEffect(() => { if (ready) refresh() }, [ready, retries])

  const handleImport = async () => {
    const input = document.createElement('input')
    input.type = 'file'; input.accept = '.epub,.fb2,.fbz'
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return
      try { await importBook(file); await refresh() } catch (e) { console.error('Import failed', e) }
    }
    input.click()
  }

  const handleSearch = () => {
    // Placeholder for Phase 5 search
  }

  return (
    <div className="flex flex-col h-full" data-testid="library-view">
      {/* Header */}
      <header className="h-[52px] bg-white border-b border-[#f0e8d9] flex items-center px-5 gap-3 shrink-0">
        <h1 className="text-xl font-bold text-[#d4641a]">Free for Read</h1>
        <div className="flex-1" />
        <button onClick={handleImport} className="px-3.5 py-1.5 rounded-full bg-[#f5efe0] text-[#b85a15] text-xs font-medium flex items-center gap-1 hover:bg-[#ede0c8] transition-colors"><Plus size={14} />导入</button>
        <button onClick={handleSearch} className="w-8 h-8 rounded-full bg-[#f5efe0] flex items-center justify-center"><Search size={14} color="#b85a15" /></button>
      </header>

      {/* Tab bar */}
      <div className="flex bg-white border-b border-[#f0e8d9] px-5 gap-0 shrink-0">
        <div className="px-5 py-3 text-sm text-[#b8a48e]">列表</div>
        <div className="px-5 py-3 text-sm text-[#d4641a] font-semibold border-b-2 border-[#d4641a]">网格</div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-5">
        {!ready || loading ? (
          <p className="text-center text-[#b8a48e] mt-20">加载中...</p>
        ) : error && books.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-[#b8a48e]">
            <p className="text-lg mb-2">加载失败</p>
            <p className="text-xs mb-4">{error}</p>
            <button onClick={() => setRetries(r => r + 1)} className="text-[#d4641a] text-sm hover:underline">重试</button>
          </div>
        ) : books.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-[#b8a48e]">
            <p className="text-lg mb-2">还没有书籍</p>
            <button onClick={handleImport} className="text-[#d4641a] text-sm hover:underline">导入第一本书</button>
          </div>
        ) : (
          <div className="grid gap-5" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))' }}>
            {books.map((book, i) => <BookCard key={book.id} book={book} index={i} onClick={() => selectBook(book.id)} />)}
            <ImportCard onClick={handleImport} />
          </div>
        )}
      </div>
    </div>
  )
}
