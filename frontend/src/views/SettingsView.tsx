import { useState, useEffect } from 'react'
import { loadSettings, saveSettings, type Settings } from '../lib/settings'

export function SettingsView() {
  const [s, setS] = useState<Settings>(loadSettings)

  useEffect(() => { saveSettings(s) }, [s])

  const u = (patch: Partial<Settings>) => setS(p => ({ ...p, ...patch }))

  return (
    <div className="flex flex-col h-full" data-testid="settings-view">
      <header className="h-[52px] bg-white border-b border-[#f0e8d9] flex items-center px-5 shrink-0">
        <h1 className="text-xl font-bold text-[#d4641a]">设置</h1>
      </header>
      <div className="flex-1 overflow-auto p-5 space-y-6 max-w-[480px]">

        <section>
          <h2 className="text-sm font-semibold text-[#3d2e1c] mb-3">AI 提供商</h2>
          <div className="space-y-3">
            <label className="block">
              <span className="text-xs text-[#b8a48e]">提供商</span>
              <select value={s.aiProvider} onChange={e => u({ aiProvider: e.target.value })}
                className="w-full mt-1 text-sm px-3 py-2 rounded-lg border border-[#f0e8d9] bg-white focus:outline-none focus:border-[#d4641a]">
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="ollama">Ollama (本地)</option>
              </select>
            </label>
            <label className="block">
              <span className="text-xs text-[#b8a48e]">API Key</span>
              <input type="password" value={s.apiKey} onChange={e => u({ apiKey: e.target.value })}
                placeholder="sk-..."
                className="w-full mt-1 text-sm px-3 py-2 rounded-lg border border-[#f0e8d9] bg-white focus:outline-none focus:border-[#d4641a]" />
            </label>
            {s.aiProvider !== 'ollama' && (
              <>
                <label className="block">
                  <span className="text-xs text-[#b8a48e]">API Base URL (可选)</span>
                  <input type="text" value={s.apiBaseUrl} onChange={e => u({ apiBaseUrl: e.target.value })}
                    placeholder="https://api.openai.com"
                    className="w-full mt-1 text-sm px-3 py-2 rounded-lg border border-[#f0e8d9] bg-white focus:outline-none focus:border-[#d4641a]" />
                </label>
                <label className="block">
                  <span className="text-xs text-[#b8a48e]">模型</span>
                  <input type="text" value={s.modelName} onChange={e => u({ modelName: e.target.value })}
                    className="w-full mt-1 text-sm px-3 py-2 rounded-lg border border-[#f0e8d9] bg-white focus:outline-none focus:border-[#d4641a]" />
                </label>
              </>
            )}
            <label className="block">
              <span className="text-xs text-[#b8a48e]">嵌入模型</span>
              <select value={s.embedProvider} onChange={e => u({ embedProvider: e.target.value })}
                className="w-full mt-1 text-sm px-3 py-2 rounded-lg border border-[#f0e8d9] bg-white focus:outline-none focus:border-[#d4641a]">
                <option value="local">本地模型 (BGE-small-zh)</option>
                <option value="openai">OpenAI</option>
              </select>
            </label>
          </div>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-[#3d2e1c] mb-3">阅读偏好</h2>
          <div className="space-y-3">
            <label className="block">
              <span className="text-xs text-[#b8a48e]">默认字号</span>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-[11px] text-[#999]">小</span>
                <input type="range" min={12} max={24} value={s.fontSize} onChange={e => u({ fontSize: Number(e.target.value) })}
                  className="flex-1 h-1 accent-[#d4641a]" />
                <span className="text-[11px] text-[#999]">大</span>
              </div>
            </label>
            <label className="block">
              <span className="text-xs text-[#b8a48e]">默认主题</span>
              <div className="flex gap-2.5 mt-1">
                {(['default','eyecare','night','parchment'] as const).map(t => (
                  <button key={t} onClick={() => u({ theme: t })}
                    className={`px-3 py-1.5 rounded-lg text-xs border-2 ${s.theme === t ? 'border-[#d4641a]' : 'border-[#f0e8d9]'}`}>
                    {{ default: '默认', eyecare: '护眼', night: '夜间', parchment: '羊皮纸' }[t]}
                  </button>
                ))}
              </div>
            </label>
          </div>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-[#3d2e1c] mb-3">关于</h2>
          <p className="text-xs text-[#b8a48e]">Free for Read v0.1.0</p>
          <a href="https://github.com/nineloong-bot/Free-for-Read" target="_blank"
            className="text-xs text-[#d4641a] hover:underline mt-1 inline-block">
            GitHub
          </a>
        </section>
      </div>
    </div>
  )
}
