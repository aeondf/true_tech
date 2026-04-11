import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Chat, Message, Theme, Model } from '../types'

const MODELS: Model[] = [
  { id: 'mws-gpt-alpha',     name: 'GPT Alpha',  description: 'Текст, вопросы',        type: 'text',          icon: '💬' },
  { id: 'kodify-2.0',        name: 'Kodify',     description: 'Код и алгоритмы',       type: 'code',          icon: '💻' },
  { id: 'cotype-preview-32k',name: 'Cotype 32K', description: 'Длинный контекст',      type: 'deep_research', icon: '🔬' },
  { id: 'auto',              name: 'Авто',       description: 'Роутер выбирает мо��ель', type: 'text',          icon: '🤖' },
]

interface AppStore {
  // User
  userId: string
  userName: string
  setUser: (id: string, name: string) => void

  // Theme
  theme: Theme
  toggleTheme: () => void

  // Chats
  chats: Chat[]
  activeChatId: string | null
  createChat: () => string
  setActiveChat: (id: string) => void
  deleteChat: (id: string) => void
  addMessage: (chatId: string, msg: Message) => void
  updateMessage: (chatId: string, msgId: string, patch: Partial<Message>) => void

  // Model
  models: Model[]
  selectedModelId: string
  autoRoute: boolean
  setModel: (id: string) => void
  setAutoRoute: (v: boolean) => void
  lastRouterDecision: { taskType: string; modelId: string; confidence: number } | null
  setRouterDecision: (d: AppStore['lastRouterDecision']) => void

  // UI
  sidebarOpen: boolean
  commandPaletteOpen: boolean
  setSidebarOpen: (v: boolean) => void
  setCommandPaletteOpen: (v: boolean) => void
}

export const useStore = create<AppStore>()(
  persist(
    (set) => ({
      userId:   crypto.randomUUID(),
      userName: '',
      setUser: (id, name) => set({ userId: id, userName: name }),

      theme: 'dark',
      toggleTheme: () => set(s => ({ theme: s.theme === 'dark' ? 'light' : 'dark' })),

      chats: [],
      activeChatId: null,
      createChat: () => {
        const id = crypto.randomUUID()
        const chat: Chat = { id, title: 'Новый чат', messages: [], createdAt: Date.now(), updatedAt: Date.now() }
        set(s => ({ chats: [chat, ...s.chats], activeChatId: id }))
        return id
      },
      setActiveChat: (id) => set({ activeChatId: id }),
      deleteChat: (id) => set(s => ({
        chats: s.chats.filter(c => c.id !== id),
        activeChatId: s.activeChatId === id ? (s.chats[0]?.id || null) : s.activeChatId,
      })),
      addMessage: (chatId, msg) => set(s => ({
        chats: s.chats.map(c => c.id !== chatId ? c : {
          ...c,
          messages: [...c.messages, msg],
          updatedAt: Date.now(),
          title: c.messages.length === 0 && msg.role === 'user'
            ? msg.content.slice(0, 40)
            : c.title,
        }),
      })),
      updateMessage: (chatId, msgId, patch) => set(s => ({
        chats: s.chats.map(c => c.id !== chatId ? c : {
          ...c,
          messages: c.messages.map(m => m.id !== msgId ? m : { ...m, ...patch }),
        }),
      })),

      models: MODELS,
      selectedModelId: 'auto',
      autoRoute: true,
      setModel: (id) => set({ selectedModelId: id, autoRoute: id === 'auto' }),
      setAutoRoute: (v) => set({ autoRoute: v }),
      lastRouterDecision: null,
      setRouterDecision: (d) => set({ lastRouterDecision: d }),

      sidebarOpen: true,
      commandPaletteOpen: false,
      setSidebarOpen: (v) => set({ sidebarOpen: v }),
      setCommandPaletteOpen: (v) => set({ commandPaletteOpen: v }),
    }),
    {
      name: 'mts-ai-hub',
      partialize: (s) => ({
        userId: s.userId, userName: s.userName,
        theme: s.theme, chats: s.chats,
        selectedModelId: s.selectedModelId, autoRoute: s.autoRoute,
      }),
    }
  )
)
