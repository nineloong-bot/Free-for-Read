import { Copy } from 'lucide-react'

export function MarkdownPreview({ markdown, title }: { markdown: string; title?: string | null }) {
  return (
    <div className="flex flex-col h-full" data-testid="markdown-preview">
      <div className="px-5 py-3 border-b border-[#f0e8d9] flex items-center gap-2 shrink-0">
        <span className="text-[13px] font-semibold text-[#3d2e1c]">预览</span>
        <div className="flex-1" />
        <span className="text-[11px] text-[#b8a48e] px-2.5 py-1 bg-[#f5efe0] rounded-md">Markdown</span>
        <button onClick={() => navigator.clipboard.writeText(markdown)} className="w-7 h-7 rounded-md flex items-center justify-center hover:bg-[#f5efe0]"><Copy size={14} stroke="#888" /></button>
      </div>
      <div className="flex-1 overflow-auto px-8 py-6">
        {title && <h1 className="text-xl font-bold text-[#3d2e1c] mb-4">{title}</h1>}
        <div className="text-sm leading-relaxed text-[#4a3f30] whitespace-pre-wrap">{markdown || '暂无内容'}</div>
      </div>
    </div>
  )
}
