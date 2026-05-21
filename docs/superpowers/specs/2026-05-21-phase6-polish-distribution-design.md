# Phase 6: Polish & Distribution Design

Date: 2026-05-21

## Goal

Make Free for Read shippable: cross-platform CI builds, automatic updates, offline-capable reading, and a settings UI for AI provider configuration.

## Scope

- GitHub Actions CI with matrix builds (macOS arm64/x86_64, Windows, Linux)
- Tauri updater integration for auto-update via GitHub Releases
- Offline mode detection and graceful degradation
- Settings view with AI provider config, reading preferences, and localStorage persistence

Out of scope: code signing/notarization, installer customization, telemetry, analytics.

## CI Build Pipeline

### Trigger

- Push to `main`: build + test (no release)
- Tag push `v*`: build + test + create GitHub Release + upload artifacts

### Matrix

| Platform | Runner | Artifact |
|----------|--------|----------|
| macOS arm64 | macos-15 | `.dmg` |
| macOS x86_64 | macos-13 | `.dmg` |
| Linux x86_64 | ubuntu-22.04 | `.AppImage` |
| Windows x86_64 | windows-2022 | `.msi` |

### Workflow File

`.github/workflows/build.yml`:

```yaml
name: Build
on:
  push:
    branches: [main]
    tags: ['v*']
jobs:
  build:
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
      - name: Install Rust
        uses: dtolnay/rust-toolchain@stable
      - name: Install deps
        run: |
          pip install uv
          uv sync --extra dev
          cd frontend && npm ci
      - name: Test backend
        run: uv run --extra dev pytest -v
      - name: Test frontend
        run: cd frontend && npx vitest run && npx tsc --noEmit
      - name: Build Tauri
        run: npx tauri build
      - uses: actions/upload-artifact@v4
        with:
          name: free-for-read-${{ matrix.target }}
          path: src-tauri/target/release/bundle/
      - name: Create Release
        if: startsWith(github.ref, 'refs/tags/v')
        uses: softprops/action-gh-release@v2
        with:
          files: src-tauri/target/release/bundle/*
```

Linux build requires `libwebkit2gtk-4.1-dev` and related system packages (handled by setup step).

## Auto-Update

### Tauri Updater

Add `tauri-plugin-updater` to `src-tauri/Cargo.toml` and `tauri.conf.json`:

```json
"plugins": {
  "updater": {
    "endpoints": ["https://github.com/nineloong-bot/Free-for-Read/releases/latest/download/latest.json"],
    "pubkey": "<generated-public-key>"
  }
}
```

Frontend: check for updates on app launch via `@tauri-apps/plugin-updater`. Show notification badge on settings icon when update available.

### Update Flow

1. App starts → background check for updates
2. If available: notification "新版本 vX.Y.Z 可用"
3. User clicks → download + install + relaunch

## Offline Mode

### Detection

Frontend `useOnlineStatus` hook:

- Listen to `window` `online`/`offline` events
- Poll `GET /health` every 30 seconds as secondary check
- Expose `isOnline: boolean` via React Context

### Behavior When Offline

| Feature | Offline Behavior |
|---------|-----------------|
| Library (list/read) | Fully available (local SQLite + files) |
| Parser (local files) | Fully available (local Python backend) |
| Parser (remote URL) | Disabled — "需要网络连接" |
| AI Chat | Disabled — "AI 功能需要网络连接" (or use local Ollama) |
| AI Search | Disabled — "搜索需要网络连接" |
| Settings | Fully available |
| Auto-update | Skipped |

Ollama local AI: if `AI_PROVIDER=ollama` and Ollama process is running locally, AI features remain available offline.

## Settings View

### Navigation

Fourth tab in BottomNav (设置). Currently shows "即将推出" placeholder. Replace with actual Settings component.

### Sections

**AI 提供商**

- Provider dropdown: OpenAI / Anthropic / Ollama
- API Key input (password field, masked)
- API Base URL (for custom endpoints)
- Model name input
- Embedding provider: 本地模型 / OpenAI

**阅读偏好**

- Default font size: slider 12-24 (default 16)
- Default theme: 默认 / 护眼 / 夜间 / 羊皮纸
- Default line spacing: slider 1.4-2.4

**关于**

- Version display
- Check for updates button
- GitHub link

### Persistence

`localStorage` key `free-for-read-settings`. On app start, read settings and apply to AppContext. On settings change, write to localStorage.

```typescript
interface Settings {
  aiProvider: string
  apiKey: string
  apiBaseUrl: string
  modelName: string
  embedProvider: string
  fontSize: number
  theme: string
  lineSpacing: number
}
```

API Key is stored in localStorage. In production, consider Tauri's secure store plugin — deferred.

## Files to Create/Modify

- Create: `.github/workflows/build.yml` — CI pipeline
- Modify: `src-tauri/Cargo.toml` — add updater plugin
- Modify: `src-tauri/tauri.conf.json` — updater config
- Create: `frontend/src/views/SettingsView.tsx` — settings UI
- Create: `frontend/src/hooks/useOnlineStatus.ts` — offline detection
- Modify: `frontend/src/contexts/AppContext.tsx` — load settings from localStorage
- Modify: `frontend/src/App.tsx` — wire SettingsView
- Modify: `frontend/src/views/ReaderView.tsx` — use default settings
- Modify: `frontend/src/api/client.ts` — add isOnline guard for AI endpoints

## Testing

### CI verification

- GitHub Actions workflow passes on push to main (build + test)
- Tag push `v0.1.0` creates GitHub Release with artifacts

### Settings tests

- Render test: SettingsView shows all sections
- localStorage round-trip: save → reload → settings restored
- API key masked in UI

### Offline tests

- Hook returns false when `/health` fails
- AI features show disabled state when offline

## Acceptance Criteria

- `git push origin main` triggers CI build that passes
- `git tag v0.1.0 && git push --tags` creates GitHub Release with 4 artifacts
- Settings view shows AI config + reading preferences
- Settings persist across app restarts
- Offline detection works (health polling)
- AI features gracefully degrade when offline
- Tauri updater plugin configured and builds
