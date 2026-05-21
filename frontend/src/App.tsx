import { BottomNav } from './components/BottomNav'
import { useApp, type View } from './contexts/AppContext'
import { LibraryView } from './views/LibraryView'
import { ReaderView } from './views/ReaderView'
import { ParserView } from './views/ParserView'

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
            {(activeView === 'ai' || activeView === 'settings') && (
              <div className="flex items-center justify-center h-full text-[#b8a48e] text-lg">
                即将推出
              </div>
            )}
          </>
        )}
      </div>
      <BottomNav activeView={activeView} onNavigate={(v: View) => navigate(v)} />
    </div>
  )
}
