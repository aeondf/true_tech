import { motion } from 'framer-motion'
import type { Message } from '../../types'

// Minimal markdown renderer
function renderMarkdown(text: string) {
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="lang-$1">$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
    .replace(/\*(.+?)\*/g, '<i>$1</i>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
    .replace(/\n/g, '<br/>')
}

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: 12,
        padding: '0 16px',
      }}
    >
      {/* Avatar for assistant */}
      {!isUser && (
        <div style={{
          width: 28, height: 28, borderRadius: 6, flexShrink: 0, marginRight: 8, marginTop: 4,
          background: 'var(--mts-red)', display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 12, fontWeight: 700, color: 'white',
        }}>А</div>
      )}

      <div style={{
        maxWidth: '75%',
        padding: '10px 14px',
        borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
        background: isUser
          ? 'var(--mts-red)'
          : 'var(--bg3)',
        color: 'var(--text)',
        fontSize: 14, lineHeight: 1.6,
        position: 'relative',
      }}>
        {/* Model badge */}
        {!isUser && message.modelId && (
          <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4, fontWeight: 500 }}>
            {message.taskType && `${taskIcon(message.taskType)} `}{message.modelId}
          </div>
        )}

        <div
          className="prose"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
        />

        {/* Streaming indicator */}
        {message.isStreaming && (
          <motion.span
            animate={{ opacity: [1, 0] }}
            transition={{ repeat: Infinity, duration: 0.8 }}
            style={{ display: 'inline-block', width: 8, height: 16, background: 'var(--mts-blue)', marginLeft: 2, borderRadius: 2 }}
          />
        )}
      </div>
    </motion.div>
  )
}

function taskIcon(t: string) {
  const icons: Record<string, string> = {
    text: '💬', code: '💻', deep_research: '🔬',
    web_search: '🔍', file_qa: '📄', image_gen: '🎨', vlm: '👁️',
  }
  return icons[t] || '🤖'
}
