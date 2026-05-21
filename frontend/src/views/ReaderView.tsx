import { useEffect, useState, useCallback } from 'react'
import { ArrowLeft } from 'lucide-react'
import { useApp } from '../contexts/AppContext'
import { getBook, getChapter, listChapters, updateProgress, createBookmark, deleteBookmark, listBookmarks, type Chapter, type ChapterSummary, type Bookmark as Bm } from '../api/client'
import { ReaderToolbar } from '../components/ReaderToolbar'
import { ReadingSettings, type ThemeId } from '../components/ReadingSettings'

const themeColors: Record<ThemeId, { bg: string; text: string; border: string }> = {
  default: { bg: '#fefcf5', text: '#4a3f30', border: '#f0e8d9' },
  eyecare: { bg: '#f5ecd7', text: '#4a3a20', border: '#e0d0a0' },
  night: { bg: '#1a1a1a', text: '#c8c0b8', border: '#2a2a2a' },
  parchment: { bg: '#e8dcc8', text: '#5a4a30', border: '#c0b090' },
}

export function ReaderView() {
  const { selectedBookId, selectBook } = useApp()
  const [title, setTitle] = useState('')
  const [author, setAuthor] = useState('')
  const [chapters, setChapters] = useState<ChapterSummary[]>([])
  const [currentChapter, setCurrentChapter] = useState<Chapter | null>(null)
  const [chapterIdx, setChapterIdx] = useState(0)
  const [theme, setTheme] = useState<ThemeId>('default')
  const [fontSize, setFontSize] = useState(16)
  const [lineSpacing, setLineSpacing] = useState(1.8)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [bookmarks, setBookmarks] = useState<Bm[]>([])
  const [loading, setLoading] = useState(true)
  const colors = themeColors[theme]

  const loadChapter = useCallback(async (idx: number) => {
    if (!selectedBookId || !chapters.length) return
    try {
      const ch = await getChapter(selectedBookId, chapters[idx].id)
      setCurrentChapter(ch); setChapterIdx(idx)
    } catch (e) { console.error('Failed to load chapter', e) }
  }, [selectedBookId, chapters])

  useEffect(() => {
    if (!selectedBookId) return
    (async () => {
      setLoading(true)
      try {
        const book = await getBook(selectedBookId)
        setTitle(book.book.title); setAuthor(book.book.author ?? '')
        const chs = await listChapters(selectedBookId); setChapters(chs.items)
        const bms = await listBookmarks(selectedBookId); setBookmarks(bms.items)
        if (chs.items.length > 0) {
          const si = book.progress ? chs.items.findIndex(c => c.id === book.progress!.chapter_id) : 0
          await loadChapter(si >= 0 ? si : 0)
        }
      } catch (e) { console.error('Failed to load book', e) }
      setLoading(false)
    })()
  }, [selectedBookId])

  // Auto-save progress on chapter change
  useEffect(() => {
    if (selectedBookId && currentChapter) {
      updateProgress(selectedBookId, currentChapter.id, { chapter_index: chapterIdx }).catch(() => {})
    }
  }, [selectedBookId, currentChapter?.id])

  const isBookmarked = bookmarks.some(b => b.chapter_id === currentChapter?.id)
  const handleBookmark = async () => {
    if (!selectedBookId || !currentChapter) return
    const ex = bookmarks.find(b => b.chapter_id === currentChapter.id)
    if (ex) { await deleteBookmark(selectedBookId, ex.id); setBookmarks(p => p.filter(b => b.id !== ex.id)) }
    else { const bm = await createBookmark(selectedBookId, currentChapter.id, { chapter_index: chapterIdx }); setBookmarks(p => [...p, bm]) }
  }

  if (!selectedBookId) return null

  return (
    <div className="flex flex-col h-full relative" style={{ backgroundColor: colors.bg }}>
      <div className="flex items-center justify-between px-5 py-3 text-[11px] shrink-0" style={{ color: colors.text, borderBottom: `1px solid ${colors.border}`, opacity: 0.6 }}>
        <button onClick={() => selectBook(null)} className="flex items-center gap-1 hover:opacity-80"><ArrowLeft size={14} />返回书库</button>
        <span>{title}{author ? ` · ${author}` : ''}</span>
        <span>{chapters.length > 0 ? `${Math.round(((chapterIdx + 1) / chapters.length) * 100)}%` : ''}</span>
      </div>
      <div className="flex-1 overflow-auto">
        {loading ? (
          <p className="text-center mt-20" style={{ color: colors.text }}>加载中...</p>
        ) : currentChapter ? (
          <div className="max-w-[640px] mx-auto px-5 py-8" style={{ fontSize, lineHeight: lineSpacing, color: colors.text }}>
            {currentChapter.markdown.split('\n').map((line, i) => {
              if (line.startsWith('# ')) return <h1 key={i} className="text-xl font-bold mb-4 text-center">{line.slice(2)}</h1>
              if (line.startsWith('## ')) return <h2 key={i} className="text-lg font-semibold mt-6 mb-3">{line.slice(3)}</h2>
              if (line.trim() === '') return <br key={i} />
              return <p key={i} className="mb-4">{line}</p>
            })}
          </div>
        ) : null}
      </div>
      <div className="shrink-0 pb-2 px-4">
        <ReaderToolbar chapterIndex={chapterIdx} chapterCount={chapters.length}
          onPrevChapter={() => chapterIdx > 0 && loadChapter(chapterIdx - 1)}
          onNextChapter={() => chapterIdx < chapters.length - 1 && loadChapter(chapterIdx + 1)}
          currentTheme={theme} onSettingsToggle={() => setSettingsOpen(!settingsOpen)}
          isBookmarked={isBookmarked} onBookmarkToggle={handleBookmark} />
      </div>
      <ReadingSettings theme={theme} onThemeChange={setTheme} fontSize={fontSize} onFontSizeChange={setFontSize} lineSpacing={lineSpacing} onLineSpacingChange={setLineSpacing} open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}
