import { beforeEach, describe, it, expect, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useOnlineStatus } from '../useOnlineStatus'
import { healthCheck } from '../../api/client'

vi.mock('../../api/client', () => ({
  healthCheck: vi.fn(),
}))

describe('useOnlineStatus', () => {
  beforeEach(() => {
    vi.mocked(healthCheck).mockReset()
  })

  it('returns true when navigator and backend are online', async () => {
    vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true)
    vi.mocked(healthCheck).mockResolvedValue()

    const { result } = renderHook(() => useOnlineStatus())

    await waitFor(() => expect(result.current).toBe(true))
  })

  it('returns false when navigator.onLine is false', async () => {
    vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false)
    const { result } = renderHook(() => useOnlineStatus())

    await waitFor(() => expect(result.current).toBe(false))
  })

  it('returns false when backend health check fails', async () => {
    vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true)
    vi.mocked(healthCheck).mockRejectedValue(new Error('Backend not ready'))

    const { result } = renderHook(() => useOnlineStatus())

    await waitFor(() => expect(result.current).toBe(false))
  })
})
