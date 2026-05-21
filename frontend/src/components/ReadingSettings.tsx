const themes = [
  { id: 'default' as const, label: '默认', bg: '#fefcf5' },
  { id: 'eyecare' as const, label: '护眼', bg: '#f5ecd7' },
  { id: 'night' as const, label: '夜间', bg: '#1a1a1a' },
  { id: 'parchment' as const, label: '羊皮纸', bg: '#e8dcc8' },
]

export type ThemeId = (typeof themes)[number]['id']

interface ReadingSettingsProps {
  theme: ThemeId; onThemeChange: (t: ThemeId) => void
  fontSize: number; onFontSizeChange: (s: number) => void
  lineSpacing: number; onLineSpacingChange: (s: number) => void
  open: boolean; onClose: () => void
}

export function ReadingSettings({ theme, onThemeChange, fontSize, onFontSizeChange, lineSpacing, onLineSpacingChange, open, onClose }: ReadingSettingsProps) {
  if (!open) return null
  return (
    <div className="absolute bottom-16 left-1/2 -translate-x-1/2 bg-white rounded-xl shadow-lg border border-[#f0e8d9] p-4 w-[320px] z-50" data-testid="reading-settings">
      <div className="mb-4">
        <p className="text-[11px] text-[#b8a48e] mb-2">字号</p>
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-[#999]">小</span>
          <input type="range" min={12} max={24} value={fontSize} onChange={e => onFontSizeChange(Number(e.target.value))} className="flex-1 h-1 accent-[#d4641a]" />
          <span className="text-[11px] text-[#999]">大</span>
        </div>
      </div>
      <div className="mb-4">
        <p className="text-[11px] text-[#b8a48e] mb-2">主题背景</p>
        <div className="flex gap-2.5">
          {themes.map(t => (
            <button key={t.id} onClick={() => onThemeChange(t.id)}
              className={`px-3.5 py-2 rounded-lg text-xs border-2 ${theme === t.id ? 'border-[#d4641a]' : 'border-[#f0e8d9]'}`}
              style={{ backgroundColor: t.bg, color: t.id === 'night' ? '#c8c0b8' : '#3d2e1c' }}>
              {t.label}
            </button>
          ))}
        </div>
      </div>
      <div>
        <p className="text-[11px] text-[#b8a48e] mb-2">行间距</p>
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-[#999]">紧凑</span>
          <input type="range" min={1.4} max={2.4} step={0.2} value={lineSpacing} onChange={e => onLineSpacingChange(Number(e.target.value))} className="flex-1 h-1 accent-[#d4641a]" />
          <span className="text-[11px] text-[#999]">宽松</span>
        </div>
      </div>
      <div className="fixed inset-0 z-40" onClick={onClose} />
    </div>
  )
}
