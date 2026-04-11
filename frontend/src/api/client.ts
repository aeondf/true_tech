const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8004'

export const api = {
  // ── Chat ─────────────────────────────────────────────
  async *streamChat(messages: {role: string; content: string}[], model = 'auto', userId: string) {
    const res = await fetch(`${BASE}/v1/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model, messages, stream: true, user: userId }),
    })
    if (!res.ok) {
      let detail = `HTTP ${res.status}`
      try {
        const body = await res.json()
        detail = body?.error?.message || body?.detail || detail
      } catch {}
      throw new Error(detail)
    }
    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() || ''
      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed.startsWith('data:')) continue
        const data = trimmed.slice(5).trim()
        if (data === '[DONE]') return
        try {
          const parsed = JSON.parse(data)
          if (parsed?.error) throw new Error(parsed.error.message || parsed.error.detail || 'API error')
          const token = parsed?.choices?.[0]?.delta?.content
          if (token) yield token as string
        } catch (e) {
          if (e instanceof Error && e.message !== 'Unexpected end of JSON input') throw e
        }
      }
    }
  },

  // ── Health ───────────────────────────────────────────
  async health() {
    const res = await fetch(`${BASE}/v1/health`)
    return res.json()
  },

  // ── Files ────────────────────────────────────────────
  async uploadFile(file: File, userId: string) {
    const form = new FormData()
    form.append('file', file)
    form.append('user_id', userId)
    const res = await fetch(`${BASE}/v1/files/upload`, { method: 'POST', body: form })
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
    return res.json()
  },

  // ── Voice ────────────────────────────────────────────
  async transcribeVoice(blob: Blob, userId: string) {
    const form = new FormData()
    form.append('audio', blob, 'voice.wav')
    form.append('user_id', userId)
    const res = await fetch(`${BASE}/v1/voice/message`, { method: 'POST', body: form })
    if (!res.ok) throw new Error(`Voice failed: ${res.status}`)
    return res.blob() // returns MP3
  },

  // ── Research (SSE) ───────────────────────────────────
  async *streamResearch(query: string, userId: string) {
    const res = await fetch(`${BASE}/v1/research`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, user_id: userId }),
    })
    if (!res.ok) throw new Error(`Research failed: ${res.status}`)
    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() || ''
      for (const line of lines) {
        if (!line.startsWith('event:') && !line.startsWith('data:')) continue
        if (line.startsWith('data:')) {
          try { yield JSON.parse(line.slice(5).trim()) } catch {}
        }
      }
    }
  },

  // ── Web Search ───────────────────────────────────────
  async webSearch(query: string) {
    const res = await fetch(`${BASE}/v1/tools/web-search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, max_results: 5 }),
    })
    return res.json()
  },

  // ── PPTX ─────────────────────────────────────────────
  async generatePptx(topic: string, slideCount = 7) {
    const res = await fetch(`${BASE}/v1/tools/generate-pptx`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, slide_count: slideCount }),
    })
    if (!res.ok) throw new Error('PPTX generation failed')
    return res.blob()
  },

  // ── Memory ───────────────────────────────────────────
  async getMemories(userId: string) {
    const res = await fetch(`${BASE}/v1/memory/${userId}`)
    return res.json()
  },
}
