import { useState, useEffect } from 'react'
import { healthCheck } from '../api/client'

export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState(navigator.onLine)

  useEffect(() => {
    let cancelled = false
    const checkBackend = async () => {
      if (!navigator.onLine) {
        setOnline(false)
        return
      }
      try {
        await healthCheck()
        if (!cancelled) setOnline(true)
      } catch {
        if (!cancelled) setOnline(false)
      }
    }
    const goOnline = () => { void checkBackend() }
    const goOffline = () => setOnline(false)
    window.addEventListener('online', goOnline)
    window.addEventListener('offline', goOffline)
    void checkBackend()
    const interval = window.setInterval(checkBackend, 30_000)
    return () => {
      cancelled = true
      window.clearInterval(interval)
      window.removeEventListener('online', goOnline)
      window.removeEventListener('offline', goOffline)
    }
  }, [])

  return online
}
