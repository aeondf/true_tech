import { useEffect } from 'react'
import { useStore } from './store'
import { LoginScreen } from './components/modals/LoginScreen'
import { Sidebar } from './components/layout/Sidebar'
import { Header } from './components/layout/Header'
import { ChatWindow } from './components/chat/ChatWindow'
import { CommandPalette } from './components/modals/CommandPalette'

export default function App() {
  const { theme, userName } = useStore()

  // Apply theme class to html
  useEffect(() => {
    document.documentElement.className = theme
  }, [theme])

  if (!userName) return <LoginScreen />

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Header />
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <Sidebar />
        <ChatWindow />
      </div>
      <CommandPalette />
    </div>
  )
}
