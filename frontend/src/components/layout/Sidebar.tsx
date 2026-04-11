import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '../../store'

export function Sidebar() {
  const { chats, activeChatId, createChat, setActiveChat, deleteChat, sidebarOpen } = useStore()

  const grouped = groupByDate(chats)

  return (
    <AnimatePresence>
      {sidebarOpen && (
        <motion.aside
          initial={{ x: -280, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: -280, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="flex flex-col h-full"
          style={{ width: 260, background: 'var(--bg2)', borderRight: '1px solid var(--border)' }}
        >
          {/* Logo + New chat */}
          <div className="flex items-center gap-3 p-4" style={{ borderBottom: '1px solid var(--border)' }}>
            <div className="mts-logo">
              <span style={{ position: 'relative' }}>
                <span style={{ position: 'absolute', top: -4, left: -4, fontSize: 8 }}>М</span>
                <span style={{ position: 'absolute', top: -4, right: -4, fontSize: 8 }}>Т</span>
                <span style={{ position: 'absolute', bottom: -4, left: -4, fontSize: 8 }}>С</span>
              </span>
            </div>
            <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--text)' }}>MTS AI Hub</span>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={createChat}
              className="ml-auto flex items-center justify-center"
              style={{
                width: 28, height: 28, borderRadius: 6,
                background: 'var(--mts-red)', color: 'white',
                border: 'none', cursor: 'pointer', fontSize: 18, lineHeight: 1,
              }}
              title="Новый чат"
            >+</motion.button>
          </div>

          {/* Chat list */}
          <div className="flex-1 overflow-y-auto p-2">
            {chats.length === 0 ? (
              <div style={{ color: 'var(--muted)', fontSize: 13, textAlign: 'center', marginTop: 40 }}>
                Нет чатов. Нажмите + чтобы начать.
              </div>
            ) : (
              Object.entries(grouped).map(([label, items]) => (
                <div key={label}>
                  <div style={{ fontSize: 11, color: 'var(--muted)', padding: '8px 8px 4px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>
                    {label}
                  </div>
                  {items.map(chat => (
                    <motion.div
                      key={chat.id}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="group flex items-center gap-2 px-3 py-2 cursor-pointer"
                      style={{
                        borderRadius: 8, marginBottom: 2,
                        background: activeChatId === chat.id ? 'var(--glass-bg)' : 'transparent',
                        border: activeChatId === chat.id ? '1px solid var(--glass-brd)' : '1px solid transparent',
                      }}
                      onClick={() => setActiveChat(chat.id)}
                    >
                      <span style={{ fontSize: 13, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text)' }}>
                        {chat.title}
                      </span>
                      <button
                        className="opacity-0 group-hover:opacity-100"
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', fontSize: 14, padding: 2, transition: 'opacity 0.2s' }}
                        onClick={e => { e.stopPropagation(); deleteChat(chat.id) }}
                        title="Удалить"
                      >✕</button>
                    </motion.div>
                  ))}
                </div>
              ))
            )}
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  )
}

function groupByDate(chats: {id: string; title: string; updatedAt: number}[]) {
  const now = Date.now()
  const groups: Record<string, typeof chats> = {}
  for (const c of chats) {
    const diff = now - c.updatedAt
    const key = diff < 86400000 ? 'Сегодня' : diff < 172800000 ? 'Вчера' : diff < 604800000 ? 'Неделя' : 'Раньше'
    if (!groups[key]) groups[key] = []
    groups[key].push(c)
  }
  return groups
}
