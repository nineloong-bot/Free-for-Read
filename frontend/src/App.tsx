import { BottomNav } from './components/BottomNav'
import { useApp, type View } from './contexts/AppContext'
import { LibraryView } from './views/LibraryView'
import { ReaderView } from './views/ReaderView'
import { ParserView } from './views/ParserView'
import { SettingsView } from './views/SettingsView'
import { AiView } from './views/AiView'

export default function App() {
  const { activeView, navigate, selectedBookId } = useApp()

  return (
    <div className="flex flex-col h-screen bg-[#faf7f2]">
      <div className="flex-1 overflow-hidden">
        {selectedBookId ? (
          <ReaderView />
        ) : (
          <>
            {activeView === 'library' && <LibraryView />}
            {activeView === 'parser' && <ParserView />}
            {activeView === 'settings' && <SettingsView />}
            {activeView === 'ai' && <AiView />}
          </>
        )}
      </div>
      <BottomNav activeView={activeView} onNavigate={(v: View) => navigate(v)} />
    </div>
  )
}
