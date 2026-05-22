import { Sparkles } from 'lucide-react'
import { SearchBar } from '../components/SearchBar'

export function AiView() {
  return (
    <div className="flex flex-col h-full">
      <header className="h-[52px] bg-white border-b border-[#f0e8d9] flex items-center px-5 shrink-0 gap-2">
        <Sparkles size={18} stroke="#d4641a" />
        <h1 className="text-xl font-bold text-[#d4641a]">AI</h1>
      </header>
      <div className="p-5 max-w-[600px] mx-auto w-full space-y-4">
        <p className="text-sm text-[#3d2e1c]">语义搜索与智能对话</p>
        <div className="bg-white rounded-xl border border-[#f0e8d9] p-4">
          <SearchBar />
        </div>
        <p className="text-xs text-[#b8a48e] leading-relaxed mt-6">
          进入书籍阅读页面，点击底部工具栏的 <span className="text-[#d4641a]">✦</span> 按钮即可打开 AI 对话侧栏，向书籍提问。
        </p>
      </div>
    </div>
  )
}
