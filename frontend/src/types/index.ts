export type Role = 'user' | 'assistant' | 'system'
export type TaskType = 'text' | 'code' | 'deep_research' | 'web_search' | 'web_parse' | 'file_qa' | 'image_gen' | 'vlm' | 'asr'
export type Theme = 'dark' | 'light'

export interface Message {
  id: string
  role: Role
  content: string
  createdAt: number
  isStreaming?: boolean
  taskType?: TaskType
  modelId?: string
  attachments?: Attachment[]
}

export interface Attachment {
  name: string
  type: 'image' | 'audio' | 'document'
  url?: string
  base64?: string
  mimeType: string
}

export interface Chat {
  id: string
  title: string
  messages: Message[]
  createdAt: number
  updatedAt: number
  model?: string
}

export interface Model {
  id: string
  name: string
  description: string
  type: TaskType
  icon: string
}

export interface RouterDecision {
  task_type: TaskType
  model_id: string
  confidence: number
}

export interface ResearchStep {
  step: number
  message?: string
  sub_queries?: string[]
  pages_fetched?: number
}
