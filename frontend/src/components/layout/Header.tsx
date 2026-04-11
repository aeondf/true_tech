import { motion } from 'framer-motion'
import { useStore } from '../../store'

export function Header() {
  const { theme, toggleTheme, setSidebarOpen, sidebarOpen, autoRoute, lastRouterDecision, setCommandPaletteOpen } = useStore()

  return (
    <header style={{
      height: 56, display: 'flex', alignItems: 'center', gap: 12, padding: '0 16px',
      borderBottom: '1px solid var(--border)', background: 'var(--bg2)', flexShrink: 0,
    }}>
      {/* Sidebar toggle */}
      <motion.button
        whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
        onClick={() => setSidebarOpen(!sidebarOpen)}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', fontSize: 18, padding: 4 }}
      >☰</motion.button>

      {/* Router decision badge */}
      {autoRoute && lastRouterDecision && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="glass"
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px', fontSize: 12 }}
        >
          <motion.span
            animate={{ opacity: [1, 0.4, 1] }}
            transition={{ repeat: Infinity, duration: 2 }}
            style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--mts-blue)', display: 'inline-block' }}
          />
          <span style={{ color: 'var(--muted)' }}>Авто:</span>
          <span style={{ color: 'var(--text)', fontWeight: 600 }}>{lastRouterDecision.modelId}</span>
          <span style={{ color: 'var(--mts-teal)', fontSize: 11 }}>
            {Math.round(lastRouterDecision.confidence * 100)}%
          </span>
        </motion.div>
      )}

      <div style={{ flex: 1 }} />

      {/* Cmd+K hint */}
      <button
        onClick={() => setCommandPaletteOpen(true)}
        style={{
          background: 'var(--glass-bg)', border: '1px solid var(--glass-brd)',
          borderRadius: 6, padding: '4px 10px', cursor: 'pointer', color: 'var(--muted)',
          fontSize: 12, display: 'flex', alignItems: 'center', gap: 6,
        }}
      >
        <kbd style={{ fontFamily: 'monospace' }}>⌘K</kbd>
        <span>Команды</span>
      </button>

      {/* Theme toggle */}
      <motion.button
        whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
        onClick={toggleTheme}
        style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, padding: 4 }}
        title="Сменить тему"
      >
        {theme === 'dark' ? '☀️' : '🌙'}
      </motion.button>
    </header>
  )
}
