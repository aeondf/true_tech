import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { useStore } from '../../store'
import { api } from '../../api/client'
import { MessageBubble } from './MessageBubble'
import { ChatInput } from './ChatInput'

export function ChatWindow() {
  const { activeChatId, chats, userId, selectedModelId, autoRoute, addMessage, updateMessage, setRouterDecision, createChat } = useStore()
  const [isLoading, setIsLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const chat = chats.find(c => c.id === activeChatId)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chat?.messages.length])

  const handleSend = async (text: string, file?: File) => {
    let cid = activeChatId
    if (!cid) cid = createChat()

    // Handle file upload
    if (file && file.type.startsWith('audio/')) {
      const msgId = crypto.randomUUID()
      addMessage(cid, { id: msgId, role: 'user', content: `🎤 Голосовое сообщение: ${file.name}`, createdAt: Date.now() })
      setIsLoading(true)
      try {
        const mp3 = await api.transcribeVoice(file, userId)
        const url = URL.createObjectURL(mp3)
        const aid = crypto.randomUUID()
        addMessage(cid, { id: aid, role: 'assistant', content: `🔊 [Аудио-ответ](${url})`, createdAt: Date.now() })
      } catch (e) {
        addMessage(cid, { id: crypto.randomUUID(), role: 'assistant', content: '❌ Ошибка голосового запроса', createdAt: Date.now() })
      } finally { setIsLoading(false) }
      return
    }

    if (file && !file.type.startsWith('audio/')) {
      try {
        await api.uploadFile(file, userId)
        const msgId = crypto.randomUUID()
        addMessage(cid, { id: msgId, role: 'user', content: `📎 Загружен файл: **${file.name}**\n${text || 'Проанализируй этот файл'}`, createdAt: Date.now() })
      } catch {
        addMessage(cid, { id: crypto.randomUUID(), role: 'assistant', content: '❌ Ошибка загрузки файла', createdAt: Date.now() })
        return
      }
    } else if (text) {
      addMessage(cid, { id: crypto.randomUUID(), role: 'user', content: text, createdAt: Date.now() })
    }

    if (!text && !file) return

    // Check if deep research
    const isResearch = /исследу|глубокий анализ|подробно разбери|изучи|проанализируй/i.test(text)
    if (isResearch) {
      await handleResearch(cid, text)
      return
    }

    // Regular chat
    setIsLoading(true)
    const assistantId = crypto.randomUUID()
    addMessage(cid, { id: assistantId, role: 'assistant', content: '', createdAt: Date.now(), isStreaming: true })

    const currentChat = useStore.getState().chats.find(c => c.id === cid)
    const messages = (currentChat?.messages || [])
      .filter(m => !m.isStreaming)
      .map(m => ({ role: m.role, content: m.content }))

    const model = autoRoute ? 'mws-gpt-alpha' : selectedModelId

    try {
      let full = ''
      for await (const token of api.streamChat(messages, model, userId)) {
        full += token
        updateMessage(cid, assistantId, { content: full })
      }
      updateMessage(cid, assistantId, { isStreaming: false, modelId: model })

      // Mock router decision for auto mode
      if (autoRoute) {
        setRouterDecision({ taskType: 'text', modelId: model, confidence: 0.92 })
      }
    } catch {
      updateMessage(cid, assistantId, { content: '❌ Ошибка подключения к API', isStreaming: false })
    } finally {
      setIsLoading(false)
    }
  }

  const handleResearch = async (cid: string, query: string) => {
    setIsLoading(true)
    const aid = crypto.randomUUID()
    addMessage(cid, { id: aid, role: 'assistant', content: '🔬 Запускаю Deep Research...', createdAt: Date.now(), isStreaming: true, taskType: 'deep_research' })
    try {
      let content = '## 🔬 Deep Research\n\n'
      for await (const event of api.streamResearch(query, userId)) {
        if (event.step === 1) content += '**Шаг 1:** Генерирую подзапросы...\n'
        if (event.sub_queries) content += `**Подзапросы:**\n${event.sub_queries.map((q: string) => `- ${q}`).join('\n')}\n\n`
        if (event.step === 3) content += '**Шаг 2:** Ищу и читаю страницы...\n'
        if (event.pages_fetched) content += `✅ Прочитано страниц: ${event.pages_fetched}\n\n`
        if (event.step === 5) content += '**Шаг 3:** Синтезирую ответ...\n\n'
        if (event.answer) content = `## 🔬 Результат исследования\n\n${event.answer}`
        updateMessage(cid, aid, { content })
      }
      updateMessage(cid, aid, { isStreaming: false, modelId: 'cotype-preview-32k' })
    } catch {
      updateMessage(cid, aid, { content: '❌ Ошибка Deep Research', isStreaming: false })
    } finally {
      setIsLoading(false)
    }
  }

  if (!activeChatId || !chat) {
    return <EmptyState />
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 0' }}>
        {chat.messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      <ChatInput onSend={handleSend} isLoading={isLoading} />
    </div>
  )
}

function EmptyState() {
  const { createChat } = useStore()
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 24 }}>
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 200 }}
        style={{ textAlign: 'center' }}
      >
        <div style={{ fontSize: 48, marginBottom: 8 }}>🤖</div>
        <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>MTS AI Hub</div>
        <div style={{ color: 'var(--muted)', fontSize: 14, marginBottom: 24 }}>Выберите чат или начните новый</div>
        <motion.button
          whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
          onClick={createChat}
          style={{
            background: 'var(--mts-red)', color: 'white', border: 'none',
            borderRadius: 10, padding: '10px 24px', fontSize: 15, fontWeight: 600,
            cursor: 'pointer',
          }}
        >Новый чат</motion.button>
      </motion.div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, maxWidth: 500, width: '100%' }}>
        {SUGGESTIONS.map(s => (
          <motion.button
            key={s.label}
            whileHover={{ scale: 1.02, borderColor: 'var(--mts-red)' }}
            onClick={() => { createChat() }}
            className="glass"
            style={{ padding: '12px 10px', cursor: 'pointer', background: 'var(--glass-bg)', border: '1px solid var(--glass-brd)', borderRadius: 10, textAlign: 'left', transition: 'all 0.2s' }}
          >
            <div style={{ fontSize: 20, marginBottom: 4 }}>{s.icon}</div>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>{s.label}</div>
            <div style={{ fontSize: 11, color: 'var(--muted)' }}>{s.desc}</div>
          </motion.button>
        ))}
      </div>
    </div>
  )
}

const SUGGESTIONS = [
  { icon: '💻', label: 'Напиши код', desc: 'Функция, класс, алгоритм' },
  { icon: '🔬', label: 'Исследуй тему', desc: 'Deep Research с источниками' },
  { icon: '📊', label: 'Создай презентацию', desc: 'PPTX по вашей теме' },
  { icon: '📄', label: 'Анализ файла', desc: 'Загрузи PDF / DOCX' },
  { icon: '🔍', label: 'Найди в сети', desc: 'Актуальная информация' },
  { icon: '🎤', label: 'Голосовой запрос', desc: 'Говорите — отвечу' },
]
