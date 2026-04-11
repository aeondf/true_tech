import { useState } from 'react'
import { motion } from 'framer-motion'
import { useStore } from '../../store'
import { HeroScene } from '../3d/HeroScene'

export function LoginScreen() {
  const [name, setName] = useState('')
  const { setUser } = useStore()

  const handleLogin = () => {
    if (!name.trim()) return
    const id = `user_${name.toLowerCase().replace(/\s+/g, '_')}_${Date.now()}`
    setUser(id, name.trim())
  }

  return (
    <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' }}>
      <HeroScene />

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 200, delay: 0.2 }}
        className="glass"
        style={{ width: 380, padding: 40, textAlign: 'center', position: 'relative', zIndex: 1 }}
      >
        {/* Logo */}
        <motion.div
          animate={{ rotate: [0, 5, -5, 0] }}
          transition={{ repeat: Infinity, duration: 4, ease: 'easeInOut' }}
          style={{
            width: 64, height: 64, background: 'var(--mts-red)', borderRadius: 12,
            margin: '0 auto 20px', display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 24, fontWeight: 900, color: 'white', letterSpacing: -1,
          }}
        >МТС</motion.div>

        <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8, color: 'var(--text)' }}>MTS AI Hub</h1>
        <p style={{ color: 'var(--muted)', fontSize: 14, marginBottom: 28 }}>Единое AI-пространство МТС</p>

        <input
          value={name}
          onChange={e => setName(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleLogin()}
          placeholder="Ваше имя"
          autoFocus
          style={{
            width: '100%', padding: '12px 14px', borderRadius: 10,
            background: 'var(--bg3)', border: '1px solid var(--border)',
            color: 'var(--text)', fontSize: 15, outline: 'none',
            fontFamily: 'inherit', marginBottom: 14,
            transition: 'border-color 0.2s',
          }}
          onFocus={e => (e.target.style.borderColor = 'var(--mts-red)')}
          onBlur={e => (e.target.style.borderColor = 'var(--border)')}
        />

        <motion.button
          whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
          onClick={handleLogin}
          disabled={!name.trim()}
          style={{
            width: '100%', padding: '12px', borderRadius: 10,
            background: name.trim() ? 'var(--mts-red)' : 'var(--bg3)',
            border: 'none', color: name.trim() ? 'white' : 'var(--muted)',
            fontSize: 15, fontWeight: 600, cursor: name.trim() ? 'pointer' : 'default',
            transition: 'all 0.2s', fontFamily: 'inherit',
          }}
        >Войти →</motion.button>
      </motion.div>
    </div>
  )
}
