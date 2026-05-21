import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { setBackendPort, healthCheck } from '../api/client'

export type View = 'library' | 'parser' | 'ai' | 'settings'

interface AppState {
  activeView: View
  backendPort: number
  selectedBookId: string | null
  ready: boolean
}

interface AppContextValue extends AppState {
  navigate: (view: View) => void
  selectBook: (id: string | null) => void
}

const AppContext = createContext<AppContextValue | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AppState>({
    activeView: 'library', backendPort: 8000, selectedBookId: null, ready: false,
  })

  useEffect(() => {
    const init = async () => {
      let port = 8000
      try {
        const { invoke } = await import('@tauri-apps/api/core')
        port = await invoke<number>('get_backend_port')
      } catch { /* use default 8000 for dev outside Tauri */ }
      setBackendPort(port)
      // Wait for backend readiness before allowing API calls
      for (let i = 0; i < 30; i++) {
        try { await healthCheck(); break } catch { await new Promise(r => setTimeout(r, 200)) }
      }
      setState(s => ({ ...s, backendPort: port, ready: true }))
    }
    init()
  }, [])

  const navigate = (view: View) => setState(s => ({ ...s, activeView: view, selectedBookId: null }))
  const selectBook = (id: string | null) => setState(s => ({ ...s, selectedBookId: id }))

  return (
    <AppContext.Provider value={{ ...state, navigate, selectBook }}>{children}</AppContext.Provider>
  )
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
