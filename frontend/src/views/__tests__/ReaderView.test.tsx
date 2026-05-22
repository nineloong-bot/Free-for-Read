import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ReaderView } from '../ReaderView'
import { getBook, getChapter, listBookmarks, listChapters } from '../../api/client'

vi.mock('../../contexts/AppContext', () => ({
  useApp: () => ({
    selectedBookId: 'book_1',
    selectBook: vi.fn(),
  }),
}))

vi.mock('../../api/client', () => ({
  getBook: vi.fn(),
  getChapter: vi.fn(),
  listChapters: vi.fn(),
  updateProgress: vi.fn().mockResolvedValue({}),
  createBookmark: vi.fn(),
  deleteBookmark: vi.fn(),
  listBookmarks: vi.fn(),
}))

describe('ReaderView', () => {
  beforeEach(() => {
    vi.mocked(getBook).mockResolvedValue({
      book: {
        id: 'book_1',
        title: 'Test Book',
        author: null,
        language: null,
        source_type: 'fb2',
        original_filename: 'book.epub',
        cover_path: null,
        word_count: 2,
        chapter_count: 1,
        created_at: '2026-05-21T00:00:00+00:00',
        updated_at: '2026-05-21T00:00:00+00:00',
      },
      chapters: [],
      progress: null,
    })
    vi.mocked(listChapters).mockResolvedValue({
      items: [{ id: 'chapter_1', book_id: 'book_1', index: 0, title: 'Opening', word_count: 2 }],
    })
    vi.mocked(getChapter).mockResolvedValue({
      id: 'chapter_1',
      book_id: 'book_1',
      index: 0,
      title: 'Opening',
      markdown: '# Opening\n\nHello reader.',
      word_count: 2,
      previous_chapter_id: null,
      next_chapter_id: null,
    })
    vi.mocked(listBookmarks).mockResolvedValue({ items: [] })
  })

  it('loads the first chapter after chapter summaries arrive', async () => {
    render(<ReaderView />)

    await waitFor(() => expect(getChapter).toHaveBeenCalledWith('book_1', 'chapter_1'))
    expect(await screen.findByText('Opening')).toBeInTheDocument()
    expect(screen.getByText('Hello reader.')).toBeInTheDocument()
  })
})
