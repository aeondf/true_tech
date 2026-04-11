import { useEffect } from 'react'
import { useStore } from './store'
import { LoginScreen } from './components/modals/LoginScreen'
import { Sidebar } from './components/layout/Sidebar'
import { Header } from './components/layout/Header'
import { ChatWindow } from './components/chat/ChatWindow'
import { CommandPalette } from './components/modals/CommandPalette'
import { SettingsPage } from './components/modals/SettingsPage'

export default function App() {
  const { theme, userName, fontSize } = useStore()

  useEffect(() => {
    document.documentElement.className = theme
  }, [theme])

  useEffect(() => {
    document.documentElement.style.fontSize =
      fontSize === 'sm' ? '13px' : fontSize === 'lg' ? '17px' : '15px'
  }, [fontSize])

  if (!userName) return <LoginScreen />

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Header />
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <Sidebar />
        <ChatWindow />
      </div>
      <CommandPalette />
      <SettingsPage />
    </div>
  )
}
