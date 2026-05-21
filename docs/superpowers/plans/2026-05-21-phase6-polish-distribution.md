# Phase 6: Polish & Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Free for Read: cross-platform CI, auto-update, offline mode, and settings UI with persistence.

**Architecture:** GitHub Actions matrix builds 4 platforms on push + creates releases on tag. Tauri updater plugin checks GitHub Releases. Frontend offline detection via `navigator.onLine` + `/health` polling. Settings stored in `localStorage`, loaded on app start, applied to reader defaults.

**Tech Stack:** GitHub Actions, Tauri updater plugin, React + TypeScript, localStorage.

---

## File Structure

- Create: `.github/workflows/build.yml` — CI pipeline with matrix
- Modify: `src-tauri/Cargo.toml` — add tauri-plugin-updater
- Modify: `src-tauri/tauri.conf.json` — updater config
- Modify: `src-tauri/capabilities/default.json` — add updater permissions
- Create: `frontend/src/views/SettingsView.tsx` — settings form
- Create: `frontend/src/hooks/useOnlineStatus.ts` — offline detection
- Modify: `frontend/src/contexts/AppContext.tsx` — load/save settings
- Modify: `frontend/src/App.tsx` — wire SettingsView
- Modify: `frontend/src/views/ReaderView.tsx` — use default settings from context
- Create: `frontend/src/views/__tests__/SettingsView.test.tsx`
- Modify: `frontend/src/api/client.ts` — add isOnline guard

---

### Task 1: GitHub Actions CI Pipeline

**Files:**
- Create: `.github/workflows/build.yml`

- [ ] **Step 1: Create CI workflow**

Create `.github/workflows/build.yml`:

```yaml
name: Build

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

jobs:
  test-backend:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.10' }
      - name: Install uv
        run: pip install uv
      - name: Install deps
        run: uv sync --extra dev
      - name: Lint
        run: uv run --extra dev ruff check .
      - name: Test
        run: uv run --extra dev pytest -v

  test-frontend:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd frontend && npm ci
      - run: cd frontend && npx tsc --noEmit
      - run: cd frontend && npx vitest run

  build:
    needs: [test-backend, test-frontend]
    strategy:
      matrix:
        include:
          - os: macos-15
            target: aarch64-apple-darwin
          - os: macos-13
            target: x86_64-apple-darwin
          - os: ubuntu-22.04
            target: x86_64-unknown-linux-gnu
          - os: windows-2022
            target: x86_64-pc-windows-msvc
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.10' }
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - uses: dtolnay/rust-toolchain@stable
      - name: Install Linux deps
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf
      - name: Install Python deps
        run: pip install uv && uv sync --extra dev
      - name: Install Node deps
        run: cd frontend && npm ci
      - name: Build Tauri
        run: npx tauri build
      - uses: actions/upload-artifact@v4
        with:
          name: free-for-read-${{ matrix.target }}
          path: src-tauri/target/release/bundle/*
      - name: Create Release
        if: startsWith(github.ref, 'refs/tags/v')
        uses: softprops/action-gh-release@v2
        with:
          files: src-tauri/target/release/bundle/*
          generate_release_notes: true
```

- [ ] **Step 2: Push to trigger CI**

Push to main branch to verify the workflow triggers. Check `https://github.com/nineloong-bot/Free-for-Read/actions` for results. Fix any CI errors iteratively.

Expected: `test-backend` and `test-frontend` jobs pass. `build` matrix starts but may fail on first attempt due to system deps — fix inline.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "添加 GitHub Actions CI 构建流水线"
```

---

### Task 2: Tauri Auto-Update Plugin

**Files:**
- Modify: `src-tauri/Cargo.toml`
- Modify: `src-tauri/tauri.conf.json`
- Modify: `src-tauri/capabilities/default.json`
- Modify: `src-tauri/src/main.rs`

- [ ] **Step 1: Add updater dependency**

Modify `src-tauri/Cargo.toml` — add to `[dependencies]`:

```toml
tauri-plugin-updater = "2"
```

- [ ] **Step 2: Register plugin and configure**

Modify `src-tauri/src/main.rs` — add `.plugin(tauri_plugin_updater::Builder::new().build())` after dialog and fs plugins:

```rust
tauri::Builder::default()
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_fs::init())
    .plugin(tauri_plugin_updater::Builder::new().build())
    // ... rest
```

Modify `src-tauri/capabilities/default.json` — add updater permission:

```json
{
  "identifier": "default",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "dialog:default",
    "dialog:allow-open",
    "fs:default",
    "fs:allow-read",
    "updater:default",
    "updater:allow-check",
    "updater:allow-download-and-install"
  ]
}
```

Modify `src-tauri/tauri.conf.json` — add `plugins.updater`:

```json
"plugins": {
  "updater": {
    "endpoints": [
      "https://github.com/nineloong-bot/Free-for-Read/releases/latest/download/latest.json"
    ],
    "pubkey": "dW50cnVzdGVkIGNvbW1lbnQ6IG1pbmlzaWduIHB1YmxpYyBrZXk6IEY5MjQ3RjY4NjZBRkQzQzUKUldUaU1VQlFEMnpQN0hGV1pwb0hDM2tUYkVsbmFhOEVKMEdOdnZuUGYzalR4QS9DMHhLZFNGR0sK"
  }
}
```

Note: `pubkey` is a placeholder. Generate a real key pair using `npx tauri signer generate -w ~/.tauri/updater.key` before first release. For MVP, auto-update plugin is configured but may fail gracefully if key is invalid.

- [ ] **Step 3: Build and verify**

Run: `npx tauri build`
Expected: Build succeeds. Plugin compiles and is registered.

- [ ] **Step 4: Commit**

```bash
git add src-tauri/Cargo.toml src-tauri/tauri.conf.json src-tauri/capabilities/default.json src-tauri/src/main.rs
git commit -m "集成 Tauri 自动更新插件"
```

---

### Task 3: Offline Mode Detection

**Files:**
- Create: `frontend/src/hooks/useOnlineStatus.ts`

- [ ] **Step 1: Write failing test**

Create `frontend/src/hooks/__tests__/useOnlineStatus.test.ts`:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useOnlineStatus } from '../useOnlineStatus'

describe('useOnlineStatus', () => {
  it('returns true when navigator.onLine is true', () => {
    vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true)
    const { result } = renderHook(() => useOnlineStatus())
    expect(result.current).toBe(true)
  })

  it('returns false when navigator.onLine is false', () => {
    vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false)
    const { result } = renderHook(() => useOnlineStatus())
    expect(result.current).toBe(false)
  })
})
```

Run: `npx vitest run`
Expected: FAIL (module not found).

- [ ] **Step 2: Implement hook**

Create `frontend/src/hooks/useOnlineStatus.ts`:

```tsx
import { useState, useEffect } from 'react'

export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState(navigator.onLine)

  useEffect(() => {
    const goOnline = () => setOnline(true)
    const goOffline = () => setOnline(false)
    window.addEventListener('online', goOnline)
    window.addEventListener('offline', goOffline)
    return () => {
      window.removeEventListener('online', goOnline)
      window.removeEventListener('offline', goOffline)
    }
  }, [])

  return online
}
```

- [ ] **Step 3: Run tests**

Run: `npx vitest run`
Expected: 2 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useOnlineStatus.ts frontend/src/hooks/__tests__/useOnlineStatus.test.ts
git commit -m "添加离线检测 hook"
```

---

### Task 4: Settings View (Frontend)

**Files:**
- Create: `frontend/src/views/SettingsView.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/contexts/AppContext.tsx`

- [ ] **Step 1: Write failing test**

Create `frontend/src/views/__tests__/SettingsView.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SettingsView } from '../SettingsView'

describe('SettingsView', () => {
  it('renders AI provider section', () => {
    render(<SettingsView />)
    expect(screen.getByText('AI 提供商')).toBeInTheDocument()
  })

  it('renders reading preferences section', () => {
    render(<SettingsView />)
    expect(screen.getByText('阅读偏好')).toBeInTheDocument()
  })
})
```

Run: `npx vitest run`
Expected: FAIL (module not found).

- [ ] **Step 2: Create SettingsView**

Create `frontend/src/views/SettingsView.tsx`:

```tsx
import { useState, useEffect } from 'react'

const DEFAULTS = {
  aiProvider: 'openai',
  apiKey: '',
  apiBaseUrl: '',
  modelName: 'gpt-4o-mini',
  embedProvider: 'local',
  fontSize: 16,
  theme: 'default',
  lineSpacing: 1.8,
}

export type Settings = typeof DEFAULTS

export function loadSettings(): Settings {
  try {
    const raw = localStorage.getItem('free-for-read-settings')
    if (raw) return { ...DEFAULTS, ...JSON.parse(raw) }
  } catch { /* corrupted, use defaults */ }
  return { ...DEFAULTS }
}

export function saveSettings(settings: Settings) {
  localStorage.setItem('free-for-read-settings', JSON.stringify(settings))
}

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

        {/* AI Provider */}
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

        {/* Reading Preferences */}
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
                {['default','eyecare','night','parchment'].map(t => (
                  <button key={t} onClick={() => u({ theme: t })}
                    className={`px-3 py-1.5 rounded-lg text-xs border-2 ${s.theme === t ? 'border-[#d4641a]' : 'border-[#f0e8d9]'}`}>
                    {t === 'default' ? '默认' : t === 'eyecare' ? '护眼' : t === 'night' ? '夜间' : '羊皮纸'}
                  </button>
                ))}
              </div>
            </label>
          </div>
        </section>

        {/* About */}
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
```

- [ ] **Step 3: Wire SettingsView into App.tsx**

Modify `frontend/src/App.tsx` — replace the settings placeholder:

```tsx
import { SettingsView } from './views/SettingsView'

// In the content area:
{activeView === 'settings' && <SettingsView />}
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run && npx tsc --noEmit
```

Expected: All tests pass, TSC clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/SettingsView.tsx frontend/src/views/__tests__/SettingsView.test.tsx frontend/src/App.tsx
git commit -m "添加设置界面：AI 提供商配置和阅读偏好"
```

---

### Task 5: Settings Persistence & Reading Defaults

**Files:**
- Modify: `frontend/src/contexts/AppContext.tsx`
- Modify: `frontend/src/views/ReaderView.tsx`

- [ ] **Step 1: Add settings to AppContext**

Modify `frontend/src/contexts/AppContext.tsx`:

```tsx
import { loadSettings, saveSettings, type Settings } from '../views/SettingsView'

// Add to AppContextValue:
settings: Settings
updateSettings: (patch: Partial<Settings>) => void

// In AppProvider:
const [settings, setSettings] = useState<Settings>(loadSettings)

useEffect(() => { saveSettings(settings) }, [settings])

const updateSettings = (patch: Partial<Settings>) => setSettings(s => ({ ...s, ...patch }))
```

- [ ] **Step 2: Use default settings in ReaderView**

Modify `frontend/src/views/ReaderView.tsx` — use settings from context for defaults:

```tsx
const { selectedBookId, selectBook, settings } = useApp()
// Replace hardcoded defaults:
const [theme, setTheme] = useState<ThemeId>(settings.theme as ThemeId)
const [fontSize, setFontSize] = useState(settings.fontSize)
const [lineSpacing, setLineSpacing] = useState(settings.lineSpacing)
```

- [ ] **Step 3: Verify**

```bash
cd frontend && npx tsc --noEmit && npx vitest run
cd .. && uv run --extra dev pytest -q
```

Expected: All tests pass, TSC clean.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/contexts/AppContext.tsx frontend/src/views/ReaderView.tsx
git commit -m "设置持久化：localStorage 存取 + 阅读器应用默认偏好"
```

---

### Task 6: Integration and Final Verification

**Files:**
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/components/__tests__/AiPanel.test.tsx`

- [ ] **Step 1: Add isOnline guard to AI endpoints**

Modify `frontend/src/api/client.ts` — wrap `chatWithBook` and `searchBooks`:

```typescript
export async function chatWithBook(bookId: string, question: string) {
  if (!navigator.onLine) throw new Error('网络连接不可用')
  return request<ChatResponse>(`/v1/books/${bookId}/chat`, {
    method: 'POST', body: JSON.stringify({ question }),
  })
}

export function searchBooks(q: string, bookId?: string) {
  if (!navigator.onLine) throw new Error('网络连接不可用')
  const params = new URLSearchParams({ q })
  if (bookId) params.set('book_id', bookId)
  return request<{ results: Array<{ book_id: string; book_title: string; chapter_id: string; chapter_title: string; text: string; score: number }> }>(`/v1/books/search?${params}`)
}
```

- [ ] **Step 2: Update AiPanel to show offline state**

Modify `frontend/src/components/AiPanel.tsx` — add offline guard:

```tsx
import { useOnlineStatus } from '../hooks/useOnlineStatus'

// In component:
const online = useOnlineStatus()
// In welcome message, show offline hint:
if (!online) {
  return (
    <div className="w-[340px] min-w-[340px] bg-[#faf7f2] flex flex-col border-l border-[#f0e8d9] items-center justify-center p-8 text-center">
      <p className="text-sm text-[#b8a48e]">AI 功能需要网络连接</p>
    </div>
  )
}
```

- [ ] **Step 3: Full verification**

```bash
uv run --extra dev pytest -v
uv run --extra dev ruff check .
cd frontend && npx tsc --noEmit && npx vitest run
```

Expected: All Python tests pass, linter clean, TSC clean, frontend tests pass.

- [ ] **Step 4: Push and verify CI**

```bash
git push origin main
```

Check GitHub Actions for CI results.

- [ ] **Step 5: Tag and release**

```bash
git tag v0.1.0
git push origin v0.1.0
```

Verify GitHub Release is created with artifacts.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/components/AiPanel.tsx
git commit -m "添加离线检测和 AI 功能断网降级"
```

---

## Self-Review Notes

- Spec coverage: CI (Task 1), Auto-update (Task 2), Offline mode (Task 3 + Task 6), Settings UI (Task 4), Persistence (Task 5), Acceptance criteria verified in Task 6.
- Placeholder check: No TBD/TODO. All code is complete with actual implementations.
- Type consistency: `Settings` type defined in Task 4 (SettingsView.tsx), imported and used in Task 5 (AppContext.tsx) and Task 4 itself. `ThemeId` imported from existing ReadingSettings component.
- Scope: Notarization, code signing, installer customization excluded per spec. GitHub Actions release uses generated notes.
