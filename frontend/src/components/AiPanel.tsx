import { useState, useRef, useEffect } from 'react'
import { Sparkles, Send, X, Loader2 } from 'lucide-react'
import { chatWithBook } from '../api/client'

interface Message {
  role: 'user' | 'assistant'
  content: string
  error?: boolean
  sources?: Array<{
    chapter_title: string; heading_path: string
    text: string; relevance: number
  }>
}

export function AiPanel(
  { bookId, bookTitle, onClose }:
  { bookId: string; bookTitle: string; onClose: () => void },
) {
  const [messages, setMessages] = useState<Message[]>([{
    role: 'assistant',
    content: `你好！你正在阅读《${bookTitle}》。有什么想了解的吗？`,
  }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)
  const lastQuestion = useRef('')

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (retryQuestion?: string) => {
    const q = retryQuestion || input.trim()
    if (!q || loading) return
    lastQuestion.current = q
    if (!retryQuestion) setInput('')
    setMessages(p => [...p, { role: 'user', content: q }])
    setLoading(true)
    try {
      const resp = await chatWithBook(bookId, q)
      setMessages(p => [...p, {
        role: 'assistant', content: resp.answer, sources: resp.sources,
      }])
    } catch {
      setMessages(p => [...p, {
        role: 'assistant', content: '抱歉，AI 请求失败。',
        error: true,
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="w-[340px] min-w-[340px] bg-[#faf7f2] flex flex-col border-l border-[#f0e8d9]" data-testid="ai-panel">
      <div className="px-4 py-3 border-b border-[#f0e8d9] flex items-center gap-2 shrink-0">
        <Sparkles size={16} stroke="#d4641a" />
        <span className="text-[13px] font-semibold text-[#3d2e1c]">AI 助手</span>
        <div className="flex-1" />
        <button onClick={onClose} className="w-6 h-6 rounded flex items-center justify-center text-[#b8a48e] hover:bg-[#f0e8d9]"><X size={14} /></button>
      </div>
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : ''}`}>
            {m.role === 'assistant' && (
              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#d4641a] to-[#e88a3a] flex items-center justify-center shrink-0 mt-0.5">
                <span className="text-white text-[10px] font-bold">AI</span>
              </div>
            )}
            <div className={`rounded-xl px-3 py-2 text-xs leading-relaxed max-w-[260px] ${
              m.role === 'user'
                ? 'bg-[#f5efe0] text-[#4a3f30]'
                : 'bg-white border border-[#f0e8d9] text-[#4a3f30]'
            }`}>
              <p>{m.content}</p>
              {m.error && (
                <button onClick={() => send(lastQuestion.current)} className="mt-2 text-[11px] text-[#d4641a] underline">
                  重试
                </button>
              )}
              {m.sources && m.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-[#f0e8d9]">
                  {m.sources.map((s, j) => (
                    <p key={j} className="text-[10px] text-[#d4641a] mt-1">
                      {s.chapter_title} · 相关度 {Math.round(s.relevance * 100)}%
                    </p>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <p className="text-xs text-[#b8a48e] flex items-center gap-1">
            <Loader2 size={12} className="animate-spin" />AI 正在思考...
          </p>
        )}
        <div ref={endRef} />
      </div>
      <div className="p-3 border-t border-[#f0e8d9] flex gap-2 shrink-0">
        <input
          value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="向 AI 提问..."
          className="flex-1 text-xs px-3 py-2 rounded-lg border border-[#f0e8d9] bg-white focus:outline-none focus:border-[#d4641a]"
        />
        <button onClick={send} disabled={loading || !input.trim()}
          className="w-8 h-8 rounded-lg bg-[#d4641a] flex items-center justify-center disabled:opacity-40">
          <Send size={14} stroke="#fff" />
        </button>
      </div>
    </div>
  )
}
