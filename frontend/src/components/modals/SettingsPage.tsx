import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '../../store'

const T = {
  ru: {
    title: 'Настройки', close: 'Закрыть',
    sections: {
      profile:    'Профиль',
      appearance: 'Внешний вид',
      chat:       'Чат',
      models:     'Модели',
      about:      'О приложении',
    },
    profile: { name: 'Имя', nameHint: 'Отображается в чатах', logout: 'Выйти из аккаунта' },
    appearance: {
      theme: 'Тема', dark: 'Тёмная', light: 'Светлая',
      language: 'Язык интерфейса', ru: 'Русский', en: 'English',
      fontSize: 'Размер шрифта', sm: 'Маленький', md: 'Средний', lg: 'Крупный',
    },
    chat: {
      sendOnEnter: 'Отправка по Enter', sendHint: 'Enter — отправить, Shift+Enter — перенос строки',
      showAvatars: 'Показывать аватары',
    },
    models: {
      autoRoute: 'Авто-маршрутизация', autoHint: 'Роутер автоматически выбирает модель под тип задачи',
      defaultModel: 'Модель по умолчанию',
    },
    about: { version: 'Версия', stack: 'Стек', backend: 'Бэкенд' },
  },
  en: {
    title: 'Settings', close: 'Close',
    sections: {
      profile:    'Profile',
      appearance: 'Appearance',
      chat:       'Chat',
      models:     'Models',
      about:      'About',
    },
    profile: { name: 'Name', nameHint: 'Shown in chats', logout: 'Sign out' },
    appearance: {
      theme: 'Theme', dark: 'Dark', light: 'Light',
      language: 'Language', ru: 'Russian', en: 'English',
      fontSize: 'Font size', sm: 'Small', md: 'Medium', lg: 'Large',
    },
    chat: {
      sendOnEnter: 'Send on Enter', sendHint: 'Enter to send, Shift+Enter for new line',
      showAvatars: 'Show avatars',
    },
    models: {
      autoRoute: 'Auto-routing', autoHint: 'Router picks the best model for the task',
      defaultModel: 'Default model',
    },
    about: { version: 'Version', stack: 'Stack', backend: 'Backend' },
  },
}

export function SettingsPage() {
  const {
    settingsOpen, setSettingsOpen,
    theme, toggleTheme,
    language, setLanguage,
    fontSize, setFontSize,
    sendOnEnter, setSendOnEnter,
    showAvatars, setShowAvatars,
    autoRoute, setAutoRoute,
    selectedModelId, setModel, models,
    userName, setUser, userId,
  } = useStore()

  const t = T[language]

  const sections = [
    { id: 'profile',    icon: '👤', label: t.sections.profile },
    { id: 'appearance', icon: '🎨', label: t.sections.appearance },
    { id: 'chat',       icon: '💬', label: t.sections.chat },
    { id: 'models',     icon: '🤖', label: t.sections.models },
    { id: 'about',      icon: 'ℹ️',  label: t.sections.about },
  ]

  return (
    <AnimatePresence>
      {settingsOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setSettingsOpen(false)}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 200, backdropFilter: 'blur(4px)' }}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.97, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 16 }}
            transition={{ type: 'spring', stiffness: 350, damping: 32 }}
            style={{
              position: 'fixed', inset: '5%', zIndex: 201, display: 'flex', borderRadius: 20,
              background: 'var(--bg2)', border: '1px solid var(--border)',
              boxShadow: '0 32px 80px rgba(0,0,0,0.5)', overflow: 'hidden',
            }}
          >
            {/* Left nav */}
            <div style={{ width: 200, borderRight: '1px solid var(--border)', padding: 20, display: 'flex', flexDirection: 'column', gap: 4, flexShrink: 0 }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text)', marginBottom: 16 }}>{t.title}</div>
              {sections.map(s => (
                <a
                  key={s.id} href={`#settings-${s.id}`}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px',
                    borderRadius: 10, fontSize: 14, color: 'var(--muted)',
                    textDecoration: 'none', transition: 'all 0.15s',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'var(--glass-bg)'; e.currentTarget.style.color = 'var(--text)' }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = 'var(--muted)' }}
                >
                  <span>{s.icon}</span><span>{s.label}</span>
                </a>
              ))}
              <div style={{ flex: 1 }} />
              <button onClick={() => setSettingsOpen(false)} style={{
                background: 'var(--glass-bg)', border: '1px solid var(--border)', borderRadius: 10,
                padding: '9px 12px', cursor: 'pointer', color: 'var(--muted)', fontSize: 14,
                fontFamily: 'inherit', textAlign: 'left',
              }}>{t.close} ✕</button>
            </div>

            {/* Right content */}
            <div style={{ flex: 1, overflowY: 'auto', padding: 32 }}>

              {/* Profile */}
              <Section id="settings-profile" title={`👤 ${t.sections.profile}`}>
                <Row label={t.profile.name} hint={t.profile.nameHint}>
                  <input
                    defaultValue={userName}
                    onBlur={e => setUser(userId, e.target.value)}
                    style={{
                      background: 'var(--bg3)', border: '1px solid var(--border)',
                      borderRadius: 10, padding: '8px 12px', color: 'var(--text)',
                      fontSize: 14, fontFamily: 'inherit', outline: 'none', width: 200,
                    }}
                    onFocus={e => (e.target.style.borderColor = 'var(--mts-red)')}
                    onBlurCapture={e => (e.target.style.borderColor = 'var(--border)')}
                  />
                </Row>
                <Row label="">
                  <DangerButton label={t.profile.logout} onClick={() => { setUser('', ''); setSettingsOpen(false) }} />
                </Row>
              </Section>

              {/* Appearance */}
              <Section id="settings-appearance" title={`🎨 ${t.sections.appearance}`}>
                <Row label={t.appearance.theme}>
                  <SegmentedControl
                    value={theme}
                    options={[{ value: 'dark', label: t.appearance.dark }, { value: 'light', label: t.appearance.light }]}
                    onChange={() => toggleTheme()}
                  />
                </Row>
                <Row label={t.appearance.language}>
                  <SegmentedControl
                    value={language}
                    options={[{ value: 'ru', label: t.appearance.ru }, { value: 'en', label: t.appearance.en }]}
                    onChange={(v) => setLanguage(v as 'ru' | 'en')}
                  />
                </Row>
                <Row label={t.appearance.fontSize}>
                  <SegmentedControl
                    value={fontSize}
                    options={[
                      { value: 'sm', label: t.appearance.sm },
                      { value: 'md', label: t.appearance.md },
                      { value: 'lg', label: t.appearance.lg },
                    ]}
                    onChange={(v) => setFontSize(v as 'sm' | 'md' | 'lg')}
                  />
                </Row>
              </Section>

              {/* Chat */}
              <Section id="settings-chat" title={`💬 ${t.sections.chat}`}>
                <Row label={t.chat.sendOnEnter} hint={t.chat.sendHint}>
                  <Toggle value={sendOnEnter} onChange={setSendOnEnter} />
                </Row>
                <Row label={t.chat.showAvatars}>
                  <Toggle value={showAvatars} onChange={setShowAvatars} />
                </Row>
              </Section>

              {/* Models */}
              <Section id="settings-models" title={`🤖 ${t.sections.models}`}>
                <Row label={t.models.autoRoute} hint={t.models.autoHint}>
                  <Toggle value={autoRoute} onChange={setAutoRoute} />
                </Row>
                <Row label={t.models.defaultModel}>
                  <select
                    value={selectedModelId}
                    onChange={e => setModel(e.target.value)}
                    style={{
                      background: 'var(--bg3)', border: '1px solid var(--border)',
                      borderRadius: 10, padding: '8px 12px', color: 'var(--text)',
                      fontSize: 14, fontFamily: 'inherit', outline: 'none', cursor: 'pointer',
                    }}
                  >
                    {models.map(m => <option key={m.id} value={m.id}>{m.icon} {m.name}</option>)}
                  </select>
                </Row>
              </Section>

              {/* About */}
              <Section id="settings-about" title={`ℹ️ ${t.sections.about}`}>
                <InfoRow label={t.about.version} value="1.0.0" />
                <InfoRow label={t.about.stack} value="React 18 + Vite + Three.js + FastAPI" />
                <InfoRow label={t.about.backend} value="http://localhost:8000/docs" isLink />
              </Section>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

// ── Sub-components ────────────────────────────────────────────────

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <div id={id} style={{ marginBottom: 40 }}>
      <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)', marginBottom: 16, paddingBottom: 8, borderBottom: '1px solid var(--border)' }}>
        {title}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>{children}</div>
    </div>
  )
}

function Row({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16, minHeight: 40 }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14, color: 'var(--text)' }}>{label}</div>
        {hint && <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>{hint}</div>}
      </div>
      {children}
    </div>
  )
}

function InfoRow({ label, value, isLink }: { label: string; value: string; isLink?: boolean }) {
  return (
    <div style={{ display: 'flex', gap: 16, padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ fontSize: 14, color: 'var(--muted)', flex: 1 }}>{label}</span>
      {isLink
        ? <a href={value} target="_blank" rel="noreferrer" style={{ fontSize: 14, color: 'var(--mts-blue)' }}>{value}</a>
        : <span style={{ fontSize: 14, color: 'var(--text)' }}>{value}</span>
      }
    </div>
  )
}

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <motion.div
      onClick={() => onChange(!value)}
      style={{
        width: 44, height: 24, borderRadius: 12, cursor: 'pointer', position: 'relative',
        background: value ? 'var(--mts-red)' : 'var(--bg3)',
        border: `1px solid ${value ? 'var(--mts-red)' : 'var(--border)'}`,
        transition: 'background 0.2s, border-color 0.2s',
        flexShrink: 0,
      }}
    >
      <motion.div
        animate={{ x: value ? 22 : 2 }}
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        style={{ position: 'absolute', top: 2, width: 18, height: 18, borderRadius: '50%', background: 'white' }}
      />
    </motion.div>
  )
}

function SegmentedControl({ value, options, onChange }: {
  value: string
  options: { value: string; label: string }[]
  onChange: (v: string) => void
}) {
  return (
    <div style={{
      display: 'flex', gap: 2, padding: 3,
      background: 'var(--bg3)', borderRadius: 10, border: '1px solid var(--border)',
    }}>
      {options.map(o => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          style={{
            padding: '5px 14px', borderRadius: 8, border: 'none', cursor: 'pointer',
            fontSize: 13, fontFamily: 'inherit', transition: 'all 0.15s',
            background: value === o.value ? 'var(--mts-red)' : 'none',
            color: value === o.value ? 'white' : 'var(--muted)',
            fontWeight: value === o.value ? 600 : 400,
          }}
        >{o.label}</button>
      ))}
    </div>
  )
}

function DangerButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <motion.button
      whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
      onClick={onClick}
      style={{
        padding: '8px 16px', borderRadius: 10, border: '1px solid rgba(237,28,36,0.4)',
        background: 'rgba(237,28,36,0.08)', color: 'var(--mts-red)',
        fontSize: 14, cursor: 'pointer', fontFamily: 'inherit', fontWeight: 500,
      }}
    >{label}</motion.button>
  )
}
