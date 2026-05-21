let backendPort: number | null = null

export function setBackendPort(port: number) {
  backendPort = port
}

function baseUrl(): string {
  if (!backendPort) throw new Error('Backend port not set')
  return `http://127.0.0.1:${backendPort}`
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const { headers: optHeaders, ...rest } = options ?? {}
  const res = await fetch(`${baseUrl()}${path}`, {
    ...rest,
    headers: { 'Content-Type': 'application/json', ...optHeaders },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const err = body?.error
    throw new Error(err?.message ?? `HTTP ${res.status}`)
  }
  return res.json() as T
}

// --- Health ---

export async function healthCheck(): Promise<void> {
  const res = await fetch(`${baseUrl()}/health`)
  if (!res.ok) throw new Error('Backend not ready')
}

// --- Types ---

export interface Book {
  id: string; title: string; author: string | null; language: string | null
  source_type: string; original_filename: string; cover_path: string | null
  word_count: number; chapter_count: number; created_at: string; updated_at: string
}

export interface ChapterSummary {
  id: string; book_id: string; index: number; title: string; word_count: number
}

export interface Chapter {
  id: string; book_id: string; index: number; title: string; markdown: string
  word_count: number; previous_chapter_id: string | null; next_chapter_id: string | null
}

export interface ReadingProgress {
  book_id: string; chapter_id: string; position: Record<string, unknown>; updated_at: string
}

export interface Bookmark {
  id: string; book_id: string; chapter_id: string; position: Record<string, unknown>
  label: string | null; created_at: string
}

export interface ParseResponse {
  markdown: string
  metadata: { title: string | null; source_url: string; source_type: string; word_count: number; processing_ms: number; content_length: number | null }
}

// --- Library API ---

export function listBooks(limit = 50, offset = 0) {
  return request<{ items: Book[] }>(`/v1/books?limit=${limit}&offset=${offset}`)
}

export function getBook(bookId: string) {
  return request<{ book: Book; chapters: ChapterSummary[]; progress: ReadingProgress | null }>(`/v1/books/${bookId}`)
}

export function getChapter(bookId: string, chapterId: string) {
  return request<Chapter>(`/v1/books/${bookId}/chapters/${chapterId}`)
}

export function listChapters(bookId: string) {
  return request<{ items: ChapterSummary[] }>(`/v1/books/${bookId}/chapters`)
}

export function getProgress(bookId: string) {
  return request<ReadingProgress | null>(`/v1/books/${bookId}/progress`)
}

export function updateProgress(bookId: string, chapterId: string, position: Record<string, unknown>) {
  return request<ReadingProgress>(`/v1/books/${bookId}/progress`, {
    method: 'PUT', body: JSON.stringify({ chapter_id: chapterId, position }),
  })
}

export function createBookmark(bookId: string, chapterId: string, position: Record<string, unknown>, label?: string) {
  return request<Bookmark>(`/v1/books/${bookId}/bookmarks`, {
    method: 'POST', body: JSON.stringify({ chapter_id: chapterId, position, label }),
  })
}

export function deleteBookmark(bookId: string, bookmarkId: string) {
  return request<void>(`/v1/books/${bookId}/bookmarks/${bookmarkId}`, { method: 'DELETE' })
}

// --- Import ---

export async function importBook(file: File) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${baseUrl()}/v1/books/import`, { method: 'POST', body: form })
  if (!res.ok) throw new Error('Import failed')
  return res.json()
}

// --- Bookmarks ---

export function listBookmarks(bookId: string) {
  return request<{ items: Bookmark[] }>(`/v1/books/${bookId}/bookmarks`)
}

// --- Parse ---

export function parseUrl(url: string) {
  return request<ParseResponse>('/v1/parse', { method: 'POST', body: JSON.stringify({ url }) })
}

export async function parseFile(file: File) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${baseUrl()}/v1/parse/file`, { method: 'POST', body: form })
  if (!res.ok) throw new Error('Parse failed')
  return res.json() as Promise<ParseResponse>
}
