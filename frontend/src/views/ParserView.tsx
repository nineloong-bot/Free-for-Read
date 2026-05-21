import { useState } from 'react'
import { FileText } from 'lucide-react'
import { parseUrl, parseFile, type ParseResponse } from '../api/client'
import { DropZone } from '../components/DropZone'
import { MarkdownPreview } from '../components/MarkdownPreview'

export function ParserView() {
  const [url, setUrl] = useState('')
  const [result, setResult] = useState<ParseResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleParseUrl = async () => {
    if (!url.trim()) return
    setLoading(true); setError(null)
    try { setResult(await parseUrl(url.trim())) } catch (e) { setError((e as Error).message) }
    finally { setLoading(false) }
  }

  const handleParseFile = async (file: File) => {
    setLoading(true); setError(null)
    try { setResult(await parseFile(file)) } catch (e) { setError((e as Error).message) }
    finally { setLoading(false) }
  }

  return (
    <div className="flex h-full gap-4 p-5" data-testid="parser-view">
      <div className="w-[320px] shrink-0 bg-white rounded-xl border border-[#f0e8d9] p-5 flex flex-col gap-4">
        <div>
          <label className="text-xs text-[#b8a48e] mb-1.5 block">远程 URL</label>
          <div className="flex gap-2">
            <input type="url" value={url} onChange={e => setUrl(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleParseUrl()} placeholder="https://example.com/article"
              className="flex-1 text-[13px] px-3 py-2 rounded-lg border border-[#f0e8d9] focus:outline-none focus:border-[#d4641a] bg-[#faf7f2]" />
            <button onClick={handleParseUrl} disabled={loading} className="px-3.5 py-2 bg-[#d4641a] text-white rounded-lg text-xs font-semibold hover:bg-[#c05a15] disabled:opacity-50 shrink-0">解析</button>
          </div>
        </div>
        <div className="flex items-center gap-3"><div className="flex-1 h-px bg-[#f0e8d9]" /><span className="text-[11px] text-[#c4b49a]">或</span><div className="flex-1 h-px bg-[#f0e8d9]" /></div>
        <DropZone onFile={handleParseFile} />
        {error && <div className="text-xs text-red-500 bg-red-50 p-2 rounded-lg">{error}</div>}
        {result && (
          <div className="flex gap-2 text-[11px] text-[#b8a48e] px-3 py-2.5 bg-[#faf7f2] rounded-lg">
            <span>{result.metadata.word_count.toLocaleString()} 字</span><div className="w-px h-3.5 bg-[#e0d4c0]" />
            <span>{result.metadata.processing_ms}ms</span><div className="w-px h-3.5 bg-[#e0d4c0]" />
            <span>{result.metadata.source_type.toUpperCase()}</span>
          </div>
        )}
        <div className="flex-1" />
      </div>
      <div className="flex-1 bg-white rounded-xl border border-[#f0e8d9] overflow-hidden">
        {result ? (
          <MarkdownPreview markdown={result.markdown} title={result.metadata.title} />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-[#b8a48e]" data-testid="parser-empty">
            <div className="w-16 h-16 rounded-2xl bg-white border border-[#f0e8d9] flex items-center justify-center mb-4">
              <FileText size={28} strokeWidth={1.5} color="#d4641a" />
            </div>
            <p className="text-base font-semibold text-[#3d2e1c] mb-1.5">解析文档</p>
            <p className="text-[13px] text-center leading-relaxed">输入 URL 或拖放文件<br/>获取干净的 Markdown 文本</p>
            <p className="text-[11px] text-[#d0c4b0] mt-6">支持 PDF · EPUB · Word · PPT · HTML · FB2</p>
          </div>
        )}
      </div>
    </div>
  )
}
