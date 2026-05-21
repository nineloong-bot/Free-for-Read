# Phase 4: Tauri Shell & Reading UI Design

Date: 2026-05-21

## Goal

Build a Tauri desktop reading app that embeds the Phase 1-3 Python backend as a sidecar. The app provides library browsing, EPUB reading via foliate-js, and document parsing with a番茄小说-inspired visual style (warm orange, flat cards, four reading themes).

## Design Language

Reference: 番茄小说 (Fanqie Novel) app.

| Element | Spec |
|---------|------|
| Primary color | #d4641a (warm orange) — active states, logo, accents |
| Background | #faf7f2 (warm white) — reduces eye fatigue |
| Cards | 10px border-radius, colored gradient covers, subtle shadow |
| Typography | System font stack, 13px body, 20px headings |
| Icons | lucide-react — 24px grid, 2px stroke, rounded caps |
| Bottom nav | Icon + label, orange when active, gray (#b8a48e) when inactive |
| Tab bar | Underline indicator, 2px orange for active tab |

Reading themes: default white (#fefcf5), eye-care yellow (#f5ecd7), night black (#1a1a1a), parchment (#e8dcc8).

All icons use lucide-react — no emoji in production code.

## Architecture

```
Tauri Desktop App
│
├── src-tauri/ (Rust)
│   ├── main.rs — spawn Python sidecar, read READY line, manage lifecycle
│   ├── sidecar.rs — process management (start, health-check, kill on exit)
│   └── tauri.conf.json — window config, sidecar declaration
│
├── frontend/ (React + TypeScript)
│   ├── src/
│   │   ├── App.tsx — router + layout shell (bottom nav + content area)
│   │   ├── views/
│   │   │   ├── LibraryView.tsx — book grid with import
│   │   │   ├── ReaderView.tsx — EPUB reader with foliate-js
│   │   │   └── ParserView.tsx — URL/file input + Markdown preview
│   │   ├── components/
│   │   │   ├── BottomNav.tsx — four-tab navigation
│   │   │   ├── BookCard.tsx — cover + title + author + progress
│   │   │   ├── ReaderToolbar.tsx — chapter nav, bookmark, theme, font size
│   │   │   ├── ReadingSettings.tsx — popover: font size, theme, line spacing
│   │   │   ├── DropZone.tsx — file drag-and-drop
│   │   │   └── MarkdownPreview.tsx — rendered Markdown output
│   │   ├── api/
│   │   │   └── client.ts — typed fetch wrapper for backend endpoints
│   │   ├── contexts/
│   │   │   └── AppContext.tsx — backend port, active view, selected book
│   │   └── lib/
│   │       └── utils.ts — shared helpers
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.ts
│
└── free_for_read/ (Python backend — already built, unchanged)
```

The Python backend has zero knowledge of Tauri. It binds 127.0.0.1 on an ephemeral port and prints `READY http://127.0.0.1:{port}`. The Rust layer captures stdout, extracts the port, and exposes it to the frontend via Tauri's invoke/state mechanism.

## Component Tree

```
App
├── BottomNav (书架 | 解析 | AI | 设置)
└── ContentArea
    ├── LibraryView
    │   ├── Header (logo + import button + search)
    │   ├── TabBar (列表 | 网格)
    │   └── BookGrid
    │       └── BookCard[] + ImportCard
    ├── ReaderView
    │   ├── foliate-js iframe/container
    │   ├── ReaderToolbar (bottom floating)
    │   └── ReadingSettings (popover)
    └── ParserView
        ├── InputPanel (URL input + DropZone + metadata)
        └── MarkdownPreview
```

## Data Flow

### Backend Communication

1. Tauri Rust spawns `free-for-read serve --port 0` as sidecar process.
2. Rust reads stdout line: `READY http://127.0.0.1:{port}`.
3. Port is stored in Tauri managed state, accessible to frontend via `invoke("get_backend_port")`.
4. Frontend constructs API URLs as `http://127.0.0.1:{port}/v1/...`.
5. On app close (or `tauri::RunEvent::Exit`), Rust sends `POST /shutdown` then kills the process.

### API Client (`frontend/src/api/client.ts`)

Typed fetch wrapper. Endpoints consumed:

| Method | Path | Purpose | View |
|--------|------|---------|------|
| GET | /v1/books?limit=&offset= | List books | Library |
| POST | /v1/books/import | Import ebook (multipart) | Library |
| GET | /v1/books/{id} | Book detail + progress | Reader |
| GET | /v1/books/{id}/chapters | List chapters | Reader |
| GET | /v1/books/{id}/chapters/{cid} | Chapter Markdown | Reader |
| GET | /v1/books/{id}/progress | Reading progress | Reader |
| PUT | /v1/books/{id}/progress | Update progress | Reader |
| POST | /v1/books/{id}/bookmarks | Create bookmark | Reader |
| GET | /v1/books/{id}/bookmarks | List bookmarks | Reader |
| DELETE | /v1/books/{id}/bookmarks/{bid} | Delete bookmark | Reader |
| POST | /v1/parse/file | Parse local file | Parser |
| POST | /v1/parse | Parse remote URL | Parser |
| GET | /health | Health check | All |

### State Management

React Context + hooks for MVP:

```typescript
interface AppState {
  backendPort: number;
  activeView: 'library' | 'parser' | 'ai' | 'settings';
  selectedBookId: string | null;
}
```

Library data fetched per-view (not global) via custom hooks (`useBooks`, `useBook`, `useChapters`). No global cache needed for MVP — refetch on view mount is acceptable.

## View Designs

### Library View

Default landing view. Warm white background.

- **Header**: Orange logo "Free for Read", import button (rounded pill, orange-tinted bg), search icon.
- **Tab bar**: 列表 / 网格 toggle (only grid for MVP, tab buttons present but 列表 is a placeholder).
- **Book grid**: CSS grid, `repeat(auto-fill, minmax(140px, 1fr))`. Each card has a colored gradient cover (assigned by book index for visual variety), rounded 10px, with shadow. Below: title (13px bold), author (11px gray), progress percentage badge. Click opens reader.
- **Import card**: Dashed border, plus icon, "导入书籍" label. Triggers native file dialog via Tauri API.
- **Empty state**: Center text "还没有书籍" with import call-to-action.

### Reader View

Full-screen reading experience.

- **Content**: foliate-js renders EPUB in an iframe or controlled container. Receives chapter content from backend API.
- **Top status bar**: Chapter title, book title, progress percentage — subtle, 11px gray text.
- **Bottom floating toolbar** (appears on click/tap):
  - Left: prev chapter / chapter X of Y / next chapter
  - Right: bookmark toggle (bookmark icon), font size (type icon), theme color dots
- **Reading settings popover** (click theme/font button):
  - Font size: slider (小 — 大)
  - Theme: 4 buttons (默认 / 护眼 / 夜间 / 羊皮纸)
  - Line spacing: slider (紧凑 — 宽松)
- **Progress sync**: Auto-save on chapter change and every 30 seconds via debounced PUT.
- **Bookmark**: Click bookmark icon toggles bookmark at current position.

### Parser View

Two-column layout. Left panel fixed width (320px), right panel fills remaining space.

- **Left panel**:
  - URL input field with "解析" button
  - "或" divider
  - File drop zone (dashed border, upload icon, "拖放文件到此处")
  - Recent items list (collapsed, placeholder for now)
  - Metadata bar: word count, processing time, source type
- **Right panel**:
  - Header: "预览" title, "Markdown" badge, copy button
  - Scrollable Markdown rendered output
- **Empty state**: Icon + "解析文档" heading + instruction text. Both panels show empty state when no content.

## Platform Integration (Rust / Tauri)

### Sidecar Lifecycle

`src-tauri/src/sidecar.rs`:

1. Locate binary: bundled in Tauri resources or in PATH.
2. Spawn process with `Command::new("free-for-read").arg("serve").arg("--port").arg("0")`.
3. Read stdout line-by-line until matching `READY http://127.0.0.1:{port}`.
4. Extract port, store in Tauri state: `app.manage(BackendPort(port))`.
5. Expose to frontend: `#[tauri::command] fn get_backend_port(state: State<BackendPort>) -> u16`.
6. On `RunEvent::Exit` or window close:
   - Send `POST http://127.0.0.1:{port}/shutdown`.
   - Wait 2 seconds.
   - Force-kill process if still alive.

### File System Access

- **Import dialog**: Use `tauri-plugin-dialog` for native file picker. Filter: `.epub, .fb2, .fbz`.
- **Drag and drop**: Use `tauri-plugin-fs` or `onDragDropEvent` for file drop on library window.
- **File associations**: Register `.epub` in `tauri.conf.json` → `bundle > fileAssociations`.

### Window Configuration

- Default size: 1200×800, min 900×600.
- Title: "Free for Read".
- Frameless: false (native title bar for MVP).
- Single window (no multi-window for MVP).

## Tech Stack

| Layer | Technology |
|-------|------------|
| Desktop shell | Tauri 2 (Rust) |
| Frontend | React 19 + TypeScript |
| Build | Vite |
| Styling | Tailwind CSS 4 + shadcn/ui |
| Icons | lucide-react |
| EPUB renderer | foliate-js |
| State | React Context + custom hooks |
| API client | fetch (native) with typed wrapper |
| Backend | Python FastAPI (Phases 1-3, unchanged) |

## Route Design (Frontend)

Single-page app with view switching via state (no React Router needed for MVP — 3 views managed by `activeView` state):

- `activeView === 'library'` → LibraryView
- `activeView === 'parser'` → ParserView
- `activeView === 'ai'` → placeholder (Phase 5)
- `activeView === 'settings'` → placeholder (Phase 6)

Reader view is a sub-state of Library: clicking a book card sets `selectedBookId` and switches to a reader mode within the content area (not a separate route).

## Testing Strategy

### Frontend Tests (Vitest + React Testing Library)

- Component render tests: BottomNav, BookCard, DropZone, MarkdownPreview.
- Hook tests: useBooks, useChapters mock API responses.
- Integration test: import flow (mock file picker → API call → book appears in grid).

### Rust Tests

- Sidecar process spawn/kill lifecycle test.
- Port extraction from READY line parsing.

### End-to-End

- Manual smoke test: Tauri app launches → backend health check → import EPUB → open reader → progress saved.
- (Automated E2E with WebDriver deferred to Phase 6.)

## Out of Scope

- AI chat, semantic search, RAG (Phase 5).
- TTS (Phase 5).
- Reading statistics (Phase 6).
- Settings UI with AI provider config (Phase 6).
- CI/CD builds (Phase 6).
- Auto-update (Phase 6).
- List view for library (grid only for MVP).
- Multi-window support.
- Frameless/custom title bar.

## Acceptance Criteria

- App launches and automatically starts Python backend.
- Bottom nav switches between Library and Parser views.
- Library view shows imported books in a card grid.
- Import button opens native file dialog; selecting an EPUB imports it via API.
- Clicking a book opens the reader view with chapter content.
- Reader bottom toolbar: chapter navigation works, bookmark toggles.
- Reading theme switching (4 themes) works in real-time.
- Progress auto-saves on chapter change.
- Parser view: URL input parses and shows Markdown preview.
- Parser view: drag-and-drop of a PDF/DOCX parses and shows preview.
- Shutdown endpoint called on app close; backend exits cleanly.
- All existing Phase 1-3 backend tests still pass.
- Frontend tests pass.
- Binary builds (`cargo tauri build`) produce a working app on the current platform.
