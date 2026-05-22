import { render, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { FoliateReader } from '../FoliateReader'
import { getBookSourceBlob } from '../../api/client'

vi.mock('foliate-js/view.js', () => ({}))

vi.mock('../../api/client', () => ({
  getBookSourceBlob: vi.fn(),
}))

describe('FoliateReader', () => {
  beforeEach(() => {
    vi.mocked(getBookSourceBlob).mockResolvedValue(new Blob(['epub bytes'], { type: 'application/epub+zip' }))

    if (!customElements.get('foliate-view')) {
      customElements.define(
        'foliate-view',
        class extends HTMLElement {
          renderer = {
            setStyles: vi.fn(),
            next: vi.fn(),
          }

          open = vi.fn().mockResolvedValue(undefined)
        },
      )
    }
  })

  it('opens the stored source file with the foliate custom element', async () => {
    render(<FoliateReader bookId="book_1" title="Test Book" theme="default" fontSize={18} lineSpacing={1.7} />)

    await waitFor(() => expect(getBookSourceBlob).toHaveBeenCalledWith('book_1'))
    const view = document.querySelector('foliate-view') as (HTMLElement & { open: ReturnType<typeof vi.fn> })
    await waitFor(() => expect(view.open).toHaveBeenCalled())
  })
})
