import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '../../store'

interface Props {
  onSend: (text: string, file?: File) => void
  isLoading: boolean
}

export function ChatInput({ onSend, isLoading }: Props) {
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [waveValues, setWaveValues] = useState<number[]>(Array(20).fill(0.3))
  const fileRef = useRef<HTMLInputElement>(null)
  const mediaRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const animRef = useRef<number>(0)
  const { setCommandPaletteOpen } = useStore()

  const handleSend = () => {
    if (!text.trim() && !file) return
    onSend(text.trim(), file || undefined)
    setText('')
    setFile(null)
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !isLoading) { e.preventDefault(); handleSend() }
    if (e.key === 'k' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); setCommandPaletteOpen(true) }
  }

  // Voice recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream)
      mediaRef.current = mr
      chunksRef.current = []
      mr.ondataavailable = e => chunksRef.current.push(e.data)
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/wav' })
        onSend('', new File([blob], 'voice.wav', { type: 'audio/wav' }))
        stream.getTracks().forEach(t => t.stop())
      }
      mr.start()
      setIsRecording(true)
      animateWave()
    } catch {}
  }

  const stopRecording = () => {
    mediaRef.current?.stop()
    setIsRecording(false)
    cancelAnimationFrame(animRef.current!)
    setWaveValues(Array(20).fill(0.3))
  }

  const animateWave = () => {
    setWaveValues(Array(20).fill(0).map(() => 0.2 + Math.random() * 0.8))
    animRef.current = requestAnimationFrame(animateWave)
  }

  // Drag & drop
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setIsDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  return (
    <div
      style={{ padding: '12px 16px', borderTop: '1px solid var(--border)', background: 'var(--bg2)', flexShrink: 0 }}
      onDragOver={e => { e.preventDefault(); setIsDragging(true) }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={onDrop}
    >
      {/* File preview */}
      <AnimatePresence>
        {file && (
          <motion.div
            initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
            className="glass" style={{ padding: '6px 10px', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}
          >
            <span>📎</span>
            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</span>
            <button onClick={() => setFile(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)' }}>✕</button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Wave visualizer */}
      <AnimatePresence>
        {isRecording && (
          <motion.div
            initial={{ height: 0, opacity: 0 }} animate={{ height: 40, opacity: 1 }} exit={{ height: 0, opacity: 0 }}
            style={{ display: 'flex', alignItems: 'center', gap: 2, marginBottom: 8, justifyContent: 'center' }}
          >
            {waveValues.map((v, i) => (
              <motion.div key={i} animate={{ scaleY: v }} style={{
                width: 3, height: 28, borderRadius: 2, transformOrigin: 'center',
                background: `linear-gradient(to top, #0066FF, #00D4AA)`,
                transition: 'transform 0.1s',
              }} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input row */}
      <div style={{
        display: 'flex', gap: 8, alignItems: 'flex-end',
        background: isDragging ? 'rgba(237,28,36,0.05)' : 'var(--bg3)',
        border: `1px solid ${isDragging ? 'var(--mts-red)' : isRecording ? 'var(--mts-red)' : 'var(--border)'}`,
        borderRadius: 12, padding: '8px 10px',
        transition: 'border-color 0.2s',
        ...(isRecording ? { boxShadow: '0 0 0 2px rgba(237,28,36,0.2)' } : {}),
      }}>
        {/* Attach */}
        <button onClick={() => fileRef.current?.click()} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', fontSize: 18, padding: 2, lineHeight: 1 }} title="Прикрепить файл">📎</button>
        <input ref={fileRef} type="file" style={{ display: 'none' }} onChange={e => { if (e.target.files?.[0]) setFile(e.target.files[0]) }} />

        {/* Textarea */}
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKey}
          placeholder={isDragging ? 'Перетащите файл...' : 'Напишите сообщение...'}
          disabled={isLoading || isRecording}
          rows={1}
          style={{
            flex: 1, background: 'none', border: 'none', outline: 'none',
            color: 'var(--text)', fontSize: 14, resize: 'none',
            fontFamily: 'inherit', lineHeight: 1.5, maxHeight: 120, overflowY: 'auto',
            padding: 0,
          }}
          onInput={e => {
            const t = e.currentTarget
            t.style.height = 'auto'
            t.style.height = Math.min(t.scrollHeight, 120) + 'px'
          }}
        />

        {/* Voice button */}
        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={isRecording ? stopRecording : startRecording}
          className={isRecording ? 'animate-pulse-red' : ''}
          style={{
            background: isRecording ? 'var(--mts-red)' : 'none',
            border: 'none', cursor: 'pointer', fontSize: 18, padding: 4, borderRadius: 6,
            color: isRecording ? 'white' : 'var(--muted)',
            transition: 'all 0.2s',
          }}
          title={isRecording ? 'Остановить запись' : 'Голосовое сообщение'}
        >🎤</motion.button>

        {/* Send */}
        <motion.button
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          onClick={handleSend}
          disabled={isLoading || (!text.trim() && !file)}
          style={{
            background: (text.trim() || file) && !isLoading ? 'var(--mts-red)' : 'var(--bg3)',
            border: '1px solid var(--border)', borderRadius: 8,
            width: 34, height: 34, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: (text.trim() || file) && !isLoading ? 'white' : 'var(--muted)',
            fontSize: 16, transition: 'all 0.2s', flexShrink: 0,
          }}
        >
          {isLoading ? (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
              style={{ width: 14, height: 14, border: '2px solid currentColor', borderTopColor: 'transparent', borderRadius: '50%' }}
            />
          ) : '↑'}
        </motion.button>
      </div>

      {/* Model selector row */}
      <ModelSelector />
    </div>
  )
}

function ModelSelector() {
  const { models, selectedModelId, setModel } = useStore()
  return (
    <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap', alignItems: 'center' }}>
      {models.map(m => (
        <motion.button
          key={m.id}
          whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
          onClick={() => setModel(m.id)}
          style={{
            padding: '3px 10px', borderRadius: 20, fontSize: 12, cursor: 'pointer',
            background: selectedModelId === m.id ? 'var(--mts-red)' : 'var(--glass-bg)',
            border: `1px solid ${selectedModelId === m.id ? 'var(--mts-red)' : 'var(--glass-brd)'}`,
            color: selectedModelId === m.id ? 'white' : 'var(--muted)',
            transition: 'all 0.2s',
          }}
        >
          {m.icon} {m.name}
        </motion.button>
      ))}
    </div>
  )
}
