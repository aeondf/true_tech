import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '../../store'

interface Command {
  id: string
  label: string
  icon: string
  shortcut?: string
  action: () => void
}

export function CommandPalette() {
  const [query, setQuery] = useState('')
  const { commandPaletteOpen, setCommandPaletteOpen, createChat, toggleTheme, theme, setModel, setSettingsOpen } = useStore()
  const inputRef = useRef<HTMLInputElement>(null)

  const COMMANDS: Command[] = [
    { id: 'new-chat',    label: 'Новый чат',           icon: '💬', shortcut: '⌘N', action: () => { createChat(); setCommandPaletteOpen(false) } },
    { id: 'settings',    label: 'Настройки',           icon: '⚙️',  shortcut: '⌘,', action: () => { setSettingsOpen(true); setCommandPaletteOpen(false) } },
    { id: 'theme',       label: `Тема: ${theme === 'dark' ? 'светлая' : 'тёмная'}`, icon: theme === 'dark' ? '☀️' : '🌙', shortcut: '⌘T', action: () => { toggleTheme(); setCommandPaletteOpen(false) } },
    { id: 'auto-model',  label: 'Модель: Авто',        icon: '🤖', action: () => { setModel('auto'); setCommandPaletteOpen(false) } },
    { id: 'gpt-model',   label: 'Модель: GPT Alpha',   icon: '💬', action: () => { setModel('mws-gpt-alpha'); setCommandPaletteOpen(false) } },
    { id: 'code-model',  label: 'Модель: Kodify',      icon: '💻', action: () => { setModel('kodify-2.0'); setCommandPaletteOpen(false) } },
    { id: 'long-model',  label: 'Модель: Cotype 32K',  icon: '🔬', action: () => { setModel('cotype-preview-32k'); setCommandPaletteOpen(false) } },
  ]

  const filtered = COMMANDS.filter(c =>
    c.label.toLowerCase().includes(query.toLowerCase())
  )

  useEffect(() => {
    if (commandPaletteOpen) { setTimeout(() => inputRef.current?.focus(), 50) }
    else setQuery('')
  }, [commandPaletteOpen])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); setCommandPaletteOpen(!commandPaletteOpen) }
      if (e.key === 'Escape') setCommandPaletteOpen(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [commandPaletteOpen])

  return (
    <AnimatePresence>
      {commandPaletteOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setCommandPaletteOpen(false)}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 100, backdropFilter: 'blur(4px)' }}
          />
          {/* Palette */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ type: 'spring', stiffness: 400, damping: 30 }}
            style={{
              position: 'fixed', top: '20%', left: '50%', transform: 'translateX(-50%)',
              width: 480, maxWidth: '90vw', zIndex: 101,
              background: 'var(--bg2)', border: '1px solid var(--border)',
              borderRadius: 14, overflow: 'hidden',
              boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
            }}
          >
            {/* Search */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 16px', borderBottom: '1px solid var(--border)' }}>
              <span style={{ color: 'var(--muted)', fontSize: 16 }}>🔍</span>
              <input
                ref={inputRef}
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Поиск команд..."
                style={{ flex: 1, background: 'none', border: 'none', outline: 'none', color: 'var(--text)', fontSize: 15, fontFamily: 'inherit' }}
              />
              <kbd style={{ fontSize: 11, color: 'var(--muted)', border: '1px solid var(--border)', borderRadius: 4, padding: '2px 6px' }}>ESC</kbd>
            </div>

            {/* Commands */}
            <div style={{ maxHeight: 300, overflowY: 'auto', padding: 6 }}>
              {filtered.map((cmd, i) => (
                <motion.button
                  key={cmd.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.03 }}
                  onClick={cmd.action}
                  style={{
                    width: '100%', display: 'flex', alignItems: 'center', gap: 10,
                    padding: '10px 12px', borderRadius: 8, cursor: 'pointer',
                    background: 'none', border: 'none', color: 'var(--text)',
                    fontSize: 14, fontFamily: 'inherit', textAlign: 'left',
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--glass-bg)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'none')}
                >
                  <span style={{ fontSize: 18 }}>{cmd.icon}</span>
                  <span style={{ flex: 1 }}>{cmd.label}</span>
                  {cmd.shortcut && (
                    <kbd style={{ fontSize: 11, color: 'var(--muted)', border: '1px solid var(--border)', borderRadius: 4, padding: '2px 6px' }}>{cmd.shortcut}</kbd>
                  )}
                </motion.button>
              ))}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
