import { useEffect, useRef, useState } from 'react'
import 'foliate-js/view.js'
import { getBookSourceBlob } from '../api/client'
import type { ThemeId } from './ReadingSettings'

type FoliateViewElement = HTMLElement & {
  open(source: Blob | File | string): Promise<void>
  renderer?: {
    setStyles?: (css: string) => void
    next?: () => void
  }
}

const themeCss: Record<ThemeId, string> = {
  default: ':root { color-scheme: light; } body { background: #fefcf5; color: #4a3f30; }',
  eyecare: ':root { color-scheme: light; } body { background: #f5ecd7; color: #4a3a20; }',
  night: ':root { color-scheme: dark; } body { background: #1a1a1a; color: #c8c0b8; }',
  parchment: ':root { color-scheme: light; } body { background: #e8dcc8; color: #5a4a30; }',
}

function setViewStyles(view: FoliateViewElement, theme: ThemeId, fontSize: number, lineSpacing: number) {
  view.renderer?.setStyles?.(`
    ${themeCss[theme]}
    body {
      font-size: ${fontSize}px;
      line-height: ${lineSpacing};
    }
  `)
}

interface FoliateReaderProps {
  bookId: string
  title: string
  theme: ThemeId
  fontSize: number
  lineSpacing: number
}

export function FoliateReader({ bookId, title, theme, fontSize, lineSpacing }: FoliateReaderProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const viewRef = useRef<FoliateViewElement | null>(null)
  const settingsRef = useRef({ theme, fontSize, lineSpacing })
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    settingsRef.current = { theme, fontSize, lineSpacing }
    if (viewRef.current) setViewStyles(viewRef.current, theme, fontSize, lineSpacing)
  }, [theme, fontSize, lineSpacing])

  useEffect(() => {
    let cancelled = false
    const container = containerRef.current
    if (!container) return

    container.replaceChildren()
    setLoading(true)
    setError(null)

    const view = document.createElement('foliate-view') as FoliateViewElement
    view.className = 'free-for-read-foliate-view'
    container.append(view)
    viewRef.current = view

    async function openBook() {
      try {
        const blob = await getBookSourceBlob(bookId)
        if (cancelled) return
        await view.open(new File([blob], `${title || bookId}.epub`, { type: blob.type || 'application/epub+zip' }))
        if (cancelled) return
        const settings = settingsRef.current
        setViewStyles(view, settings.theme, settings.fontSize, settings.lineSpacing)
        view.renderer?.next?.()
        setLoading(false)
      } catch (e) {
        console.error('Failed to open EPUB with foliate-js', e)
        if (!cancelled) {
          setError('无法打开 EPUB 源文件')
          setLoading(false)
        }
      }
    }

    void openBook()

    return () => {
      cancelled = true
      if (viewRef.current === view) viewRef.current = null
      view.remove()
    }
  }, [bookId, title])

  return (
    <div className="relative h-full">
      <div ref={containerRef} className="h-full" />
      {loading && (
        <p className="absolute inset-x-0 top-20 text-center text-sm opacity-70">加载中...</p>
      )}
      {error && (
        <p className="absolute inset-x-0 top-20 text-center text-sm text-red-600">{error}</p>
      )}
    </div>
  )
}
