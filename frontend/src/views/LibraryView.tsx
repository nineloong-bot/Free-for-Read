import { useCallback, useEffect, useState } from 'react'
import { CheckSquare, Plus, Trash2, X } from 'lucide-react'
import { deleteBook, listBooks, importBook, reindexBook, type Book } from '../api/client'
import { BookCard, ImportCard } from '../components/BookCard'
import { coverGradient } from '../lib/utils'
import { SearchBar } from '../components/SearchBar'
import { useApp } from '../contexts/AppContext'

export function LibraryView() {
  const { selectBook, ready } = useApp()
  const [books, setBooks] = useState<Book[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retries, setRetries] = useState(0)
  const [selectMode, setSelectMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [deleting, setDeleting] = useState(false)
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('grid')

  const refresh = useCallback(async () => {
    try { setLoading(true); setError(null); const data = await listBooks(); setBooks(data.items) }
    catch (e) { setError((e as Error).message); console.error('Failed to load books', e) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { if (ready) refresh() }, [ready, retries, refresh])

  const handleImport = async () => {
    const input = document.createElement('input')
    input.type = 'file'; input.accept = '.epub,.fb2,.fbz'
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return
      try {
        const imported = await importBook(file)
        // Auto-index for search
        reindexBook(imported.book.id).catch(() => {})
        await refresh()
      } catch (e) { console.error('Import failed', e) }
    }
    input.click()
  }

  const handleToggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  const handleDeleteSingle = async (id: string) => {
    if (!confirm('确认删除此书？')) return
    await deleteBook(id)
    setBooks(p => p.filter(b => b.id !== id))
  }

  const handleBatchDelete = async () => {
    if (!confirm(`确认删除选中的 ${selectedIds.size} 本书？`)) return
    setDeleting(true)
    for (const id of selectedIds) {
      try { await deleteBook(id) } catch { /* continue */ }
    }
    setSelectedIds(new Set())
    setSelectMode(false)
    setDeleting(false)
    await refresh()
  }

  const exitSelectMode = () => {
    setSelectMode(false)
    setSelectedIds(new Set())
  }

  return (
    <div className="flex flex-col h-full" data-testid="library-view">
      {/* Header */}
      <header className="h-[52px] bg-white border-b border-[#f0e8d9] flex items-center px-5 gap-3 shrink-0">
        {selectMode ? (
          <>
            <button onClick={exitSelectMode} className="flex items-center gap-1 text-sm text-[#3d2e1c]"><X size={16} /></button>
            <span className="text-sm text-[#3d2e1c] font-medium">{selectedIds.size} 本选中</span>
            <div className="flex-1" />
            <button onClick={handleBatchDelete} disabled={selectedIds.size === 0 || deleting}
              className="px-3 py-1.5 rounded-full bg-red-50 text-red-500 text-xs font-medium flex items-center gap-1">
              <Trash2 size={14} />删除
            </button>
          </>
        ) : (
          <>
            <h1 className="text-xl font-bold text-[#d4641a]">Free for Read</h1>
            <div className="flex-1" />
            <button onClick={() => setSelectMode(true)} className="w-8 h-8 rounded-full bg-[#f5efe0] flex items-center justify-center"><CheckSquare size={14} color="#b85a15" /></button>
            <button onClick={handleImport} className="px-3.5 py-1.5 rounded-full bg-[#f5efe0] text-[#b85a15] text-xs font-medium flex items-center gap-1 hover:bg-[#ede0c8] transition-colors"><Plus size={14} />导入</button>
          </>
        )}
      </header>

      {/* Tab bar */}
      <div className="flex bg-white border-b border-[#f0e8d9] px-5 gap-0 shrink-0">
        <button onClick={() => setViewMode('list')}
          className={`px-5 py-3 text-sm ${viewMode === 'list' ? 'text-[#d4641a] font-semibold border-b-2 border-[#d4641a]' : 'text-[#b8a48e]'}`}>
          列表
        </button>
        <button onClick={() => setViewMode('grid')}
          className={`px-5 py-3 text-sm ${viewMode === 'grid' ? 'text-[#d4641a] font-semibold border-b-2 border-[#d4641a]' : 'text-[#b8a48e]'}`}>
          网格
        </button>
      </div>

      {/* Search */}
      <div className="px-5 py-2 bg-white border-b border-[#f0e8d9]"><SearchBar /></div>

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
        ) : viewMode === 'list' ? (
          <div className="flex flex-col gap-1">
            {books.map((book, i) => (
              <div key={book.id} className="flex items-center gap-3 bg-white rounded-lg border border-[#f0e8d9] px-4 py-3 hover:bg-[#faf7f2] cursor-pointer"
                onClick={() => selectBook(book.id)}>
                <div className="w-10 h-14 rounded-md shrink-0" style={{ background: coverGradient(i) }} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-[#3d2e1c] truncate">{book.title}</p>
                  <p className="text-xs text-[#b8a48e]">{book.author ?? '未知作者'}</p>
                </div>
                <span className="text-xs text-[#b8a48e]">{book.word_count.toLocaleString()} 字 · {book.chapter_count} 章</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid gap-5" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))' }}>
            {books.map((book, i) => (
              <BookCard key={book.id} book={book} index={i}
                onClick={() => selectBook(book.id)}
                selectMode={selectMode}
                selected={selectedIds.has(book.id)}
                onToggleSelect={() => handleToggleSelect(book.id)}
                onDelete={() => handleDeleteSingle(book.id)} />
            ))}
            {!selectMode && <ImportCard onClick={handleImport} />}
          </div>
        )}
      </div>
    </div>
  )
}
