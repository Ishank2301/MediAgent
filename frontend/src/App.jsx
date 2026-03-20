import { useState, useEffect, useRef, useCallback } from 'react'
import * as API from './api/client'

// ── Theme ────────────────────────────────────────────────────────────────────
function useTheme() {
  const [dark, setDark] = useState(() => localStorage.getItem('ma-theme') === 'dark')
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('ma-theme', dark ? 'dark' : 'light')
  }, [dark])
  return [dark, () => setDark(d => !d)]
}

// ── Constants ────────────────────────────────────────────────────────────────
const MODES = {
  general:      { label: 'General',      emoji: '🤖', grad: 'from-slate-500 to-slate-700',  hint: 'Ask anything health-related' },
  symptom:      { label: 'Symptoms',     emoji: '🩺', grad: 'from-blue-500 to-blue-700',    hint: 'Describe and assess symptoms' },
  interaction:  { label: 'Drug Check',   emoji: '💊', grad: 'from-amber-500 to-amber-700',  hint: 'Check drug interactions' },
  prescription: { label: 'Prescription', emoji: '📋', grad: 'from-violet-500 to-violet-700', hint: 'Understand prescriptions' },
}

const TOOLS = [
  { id:'appointments', emoji:'📅', label:'Appointments',    desc:'Plan & get reminders' },
  { id:'notify',       emoji:'🔔', label:'Notifications',   desc:'Email & WhatsApp alerts' },
  { id:'search',       emoji:'🌐', label:'Web Search',      desc:'Live drug & news search' },
  { id:'drug',         emoji:'💊', label:'Drug Checker',    desc:'Interaction risk analysis' },
  { id:'medicine',     emoji:'🔬', label:'Medicine Info',   desc:'FDA drug database' },
  { id:'medtracker',   emoji:'💉', label:'Med Tracker',     desc:'Adherence & schedules' },
  { id:'bmi',          emoji:'⚖️', label:'BMI Calculator',  desc:'Health metric tool' },
]


const RISK_CLS = {
  emergency: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-950/40 dark:text-red-300 dark:border-red-900',
  urgent:    'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900',
  routine:   'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-900',
  CRITICAL:  'bg-red-100 text-red-800 border-red-300 dark:bg-red-950/60 dark:text-red-200 dark:border-red-800',
  HIGH:      'bg-red-50 text-red-700 border-red-200 dark:bg-red-950/40 dark:text-red-300 dark:border-red-900',
  MEDIUM:    'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900',
  LOW:       'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-900',
}
const RISK_ICO = { emergency:'🚨', urgent:'⚠️', routine:'✅', CRITICAL:'💀', HIGH:'🔴', MEDIUM:'🟡', LOW:'🟢' }
const FREQ_LABELS = { once_daily:'Once daily', twice_daily:'Twice daily', three_times_daily:'3× daily', four_times_daily:'4× daily', weekly:'Weekly', as_needed:'As needed' }

// ── Utilities ─────────────────────────────────────────────────────────────────
const Badge = ({ level }) => (
  <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${RISK_CLS[level] || RISK_CLS.routine}`}>
    {RISK_ICO[level]} {level}
  </span>
)

function timeAgo(iso) {
  if (!iso) return ''
  const s = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return new Date(iso).toLocaleDateString()
}
function fmtDateTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
function dlBlob(blob, name) {
  const u = URL.createObjectURL(blob)
  Object.assign(document.createElement('a'), { href: u, download: name }).click()
  setTimeout(() => URL.revokeObjectURL(u), 1000)
}

// Primitive components
const Card = ({ className = '', children, ...p }) => (
  <div className={`bg-[var(--warm-white)] dark:bg-[#1a2420] border border-[var(--border)] rounded-2xl ${className}`} {...p}>
    {children}
  </div>
)
const Btn = ({ v = 'primary', sm, className = '', children, ...p }) => {
  const base = `inline-flex items-center justify-center gap-2 font-medium transition-all active:scale-[0.97] disabled:opacity-40 disabled:cursor-not-allowed rounded-xl ${sm ? 'text-xs px-3 py-1.5' : 'text-sm px-4 py-2.5'}`
  const vars = {
    primary: 'bg-[var(--forest)] hover:bg-[var(--forest-mid)] text-white shadow-sm',
    soft:    'bg-[var(--mint)] dark:bg-[#1e3028] hover:opacity-80 text-[var(--forest)] dark:text-emerald-300 border border-[var(--sage)] border-opacity-40',
    ghost:   'hover:bg-[var(--mint)] dark:hover:bg-[#1e2e26] text-[var(--muted)] hover:text-[var(--forest)] dark:hover:text-emerald-300',
    danger:  'bg-red-500 hover:bg-red-600 text-white shadow-sm',
    outline: 'border border-[var(--border)] hover:border-[var(--forest-light)] text-[var(--ink)] hover:text-[var(--forest)] dark:text-[var(--ink)]',
  }
  return <button className={`${base} ${vars[v] || vars.primary} ${className}`} {...p}>{children}</button>
}
const Input = ({ label, wClass = '', className = '', ...p }) => (
  <div className={wClass}>
    {label && <label className="block text-xs font-medium text-[var(--muted)] mb-1.5">{label}</label>}
    <input className={`w-full rounded-xl border border-[var(--border)] bg-[var(--warm-white)] dark:bg-[#1a2420] text-[var(--ink)] placeholder:text-[var(--muted)] placeholder:opacity-60 px-3.5 py-2.5 text-sm focus-forest transition-colors ${className}`} {...p} />
  </div>
)
const Select = ({ label, wClass = '', children, ...p }) => (
  <div className={wClass}>
    {label && <label className="block text-xs font-medium text-[var(--muted)] mb-1.5">{label}</label>}
    <select className="w-full rounded-xl border border-[var(--border)] bg-[var(--warm-white)] dark:bg-[#1a2420] text-[var(--ink)] px-3.5 py-2.5 text-sm focus-forest" {...p}>{children}</select>
  </div>
)

// ── Message markdown renderer ─────────────────────────────────────────────────
function MsgBody({ text }) {
  if (!text) return null
  return (
    <div className="space-y-1.5 text-sm leading-relaxed">
      {text.split('\n').map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-1" />
        if (line.startsWith('### ')) return <p key={i} className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)] mt-3 mb-0.5">{line.slice(4)}</p>
        if (line.startsWith('## '))  return <h4 key={i} className="font-semibold text-base mt-3 mb-1">{line.slice(3)}</h4>
        if (line.startsWith('# '))   return <h3 key={i} className="font-display font-bold text-lg mt-3 mb-1">{line.slice(2)}</h3>
        if (/^\*\*(.+)\*\*$/.test(line)) return <p key={i} className="font-semibold mt-2">{line.replace(/\*\*/g, '')}</p>
        if (line.startsWith('- ') || line.startsWith('• '))
          return <div key={i} className="flex gap-2.5"><span className="text-[var(--forest-light)] dark:text-emerald-400 flex-shrink-0 mt-0.5 font-bold">›</span><span>{line.slice(2)}</span></div>
        const nm = line.match(/^(\d+)\.\s(.+)/)
        if (nm) return (
          <div key={i} className="flex gap-2.5">
            <span className="w-5 h-5 rounded-full bg-[var(--forest)]/10 dark:bg-emerald-900/30 text-[var(--forest)] dark:text-emerald-400 text-xs flex items-center justify-center flex-shrink-0 mt-0.5 font-bold">{nm[1]}</span>
            <span>{nm[2]}</span>
          </div>
        )
        const parts = line.split(/(\*\*[^*]+\*\*)/)
        return <p key={i}>{parts.map((p, j) => p.startsWith('**') ? <strong key={j}>{p.replace(/\*\*/g, '')}</strong> : p)}</p>
      })}
    </div>
  )
}

// ── CHAT WINDOW ───────────────────────────────────────────────────────────────
function ChatWindow({ session, onUpdate }) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [msgs, setMsgs] = useState(session?.messages || [])
  const [exporting, setExporting] = useState(false)
  const [pendingFile, setPendingFile] = useState(null)   // {file, preview, type}
  const bottomRef = useRef(null)
  const inputRef  = useRef(null)
  const fileRef   = useRef(null)
  const mode = MODES[session?.mode] || MODES.general

  useEffect(() => { setMsgs(session?.messages || []) }, [session?.id])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, loading])

  const send = async () => {
    const text = input.trim()
    if ((!text && !pendingFile) || loading) return

    // File upload path
    if (pendingFile) {
      const displayMsg = text ? `[📎 ${pendingFile.file.name}] ${text}` : `[📎 ${pendingFile.file.name}]`
      setInput('')
      const pf = pendingFile
      setPendingFile(null)
      setMsgs(p => [...p, { role: 'user', content: displayMsg, isFile: true, timestamp: new Date().toISOString() }])
      setLoading(true)
      try {
        const res = await API.sendFile(session.id, pf.file, text, session.mode)
        setMsgs(p => [...p, { role: 'assistant', content: res.response, meta: res.meta, timestamp: new Date().toISOString() }])
        onUpdate?.()
      } catch (e) {
        setMsgs(p => [...p, { role: 'assistant', content: `⚠️ Upload failed: ${e.message}`, timestamp: new Date().toISOString() }])
      } finally { setLoading(false) }
      return
    }

    // Text-only path
    setInput('')
    setMsgs(p => [...p, { role: 'user', content: text, timestamp: new Date().toISOString() }])
    setLoading(true)
    try {
      const res = await API.sendMessage(session.id, text, session.mode)
      setMsgs(p => [...p, { role: 'assistant', content: res.response, meta: res.meta, timestamp: new Date().toISOString() }])
      onUpdate?.()
    } catch (e) {
      setMsgs(p => [...p, { role: 'assistant', content: `⚠️ ${e.message || 'Error — check your API key or Ollama status'}`, timestamp: new Date().toISOString() }])
    } finally { setLoading(false); setTimeout(() => inputRef.current?.focus(), 50) }
  }

  const pickFile = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const isImg = file.type.startsWith('image/')
    const isPdf = file.type === 'application/pdf'
    if (!isImg && !isPdf) {
      alert('Only images (JPEG, PNG, WebP, GIF) and PDF files are supported.')
      e.target.value = ''; return
    }
    if (file.size > 10 * 1024 * 1024) {
      alert('File too large. Maximum size is 10MB.')
      e.target.value = ''; return
    }
    const preview = isImg ? URL.createObjectURL(file) : null
    setPendingFile({ file, preview, type: isImg ? 'image' : 'pdf' })
    e.target.value = ''
  }

  const removePendingFile = () => {
    if (pendingFile?.preview) URL.revokeObjectURL(pendingFile.preview)
    setPendingFile(null)
  }

  const exportPdf = async () => {
    setExporting(true)
    try { dlBlob(await API.exportSession(session.id), `mediagent-session-${session.id.slice(0,8)}.pdf`) }
    catch { alert('PDF export failed — ensure reportlab is installed: pip install reportlab') }
    finally { setExporting(false) }
  }

  const STARTERS = {
    symptom:      ['I have a headache and fever', 'Chest pain and shortness of breath', 'Nausea and dizziness for 3 days'],
    interaction:  ['I take aspirin and warfarin daily', 'Are metformin and ibuprofen safe together?'],
    prescription: ['Help me understand my prescription', 'I was prescribed amoxicillin 500mg 3x daily'],
    general:      ['What are ibuprofen\'s side effects?', 'How does metformin work?', 'What is hypertension?'],
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-3.5 border-b border-[var(--border)] bg-[var(--warm-white)] dark:bg-[#111815] flex-shrink-0">
        <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${mode.grad} flex items-center justify-center text-base flex-shrink-0 shadow-sm`}>{mode.emoji}</div>
        <div className="flex-1 min-w-0">
          <p className="font-display font-semibold text-[var(--ink)] truncate text-sm">{session?.title}</p>
          <p className="text-xs text-[var(--muted)]">{mode.label} · {msgs.length} messages</p>
        </div>
        {msgs.length > 0 && (
          <Btn v="soft" sm onClick={exportPdf} disabled={exporting}>
            📄 {exporting ? 'Exporting…' : 'PDF'}
          </Btn>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-4 bg-[var(--cream)] dark:bg-[#0d1512]">
        {msgs.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-5 py-10">
            <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${mode.grad} flex items-center justify-center text-3xl shadow-xl`}>{mode.emoji}</div>
            <div>
              <p className="font-display font-bold text-[var(--ink)] text-xl">{mode.label}</p>
              <p className="text-[var(--muted)] text-sm mt-1.5 max-w-xs">{mode.hint}. This chat is persistent — your history is always saved.</p>
            </div>
            <div className="flex flex-wrap gap-2 justify-center max-w-sm">
              {(STARTERS[session?.mode] || STARTERS.general).map(s => (
                <button key={s} onClick={() => setInput(s)} className="text-xs bg-[var(--warm-white)] dark:bg-[#1a2420] hover:bg-[var(--mint)] dark:hover:bg-[#1e2e26] text-[var(--ink)] px-3.5 py-2 rounded-full border border-[var(--border)] transition-colors">{s}</button>
              ))}
            </div>
          </div>
        )}

        {msgs.map((msg, i) => (
          <div key={i} className={`flex gap-2.5 anim-up ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className={`w-7 h-7 rounded-xl bg-gradient-to-br ${mode.grad} flex items-center justify-center text-xs flex-shrink-0 mt-0.5 shadow-sm`}>{mode.emoji}</div>
            )}
            <div className={`max-w-[82%] px-4 py-3 shadow-sm ${msg.role === 'user' ? 'bubble-user' : 'bubble-ai dark:bg-[#1a2420]'}`}>
              {msg.role === 'user'
                ? <p className="text-sm leading-relaxed">{msg.content}</p>
                : <MsgBody text={msg.content} />
              }
              {msg.meta?.triage?.level && (
                <div className="mt-2.5 pt-2.5 border-t border-black/5 dark:border-white/5 flex flex-wrap items-center gap-2">
                  <span className="text-xs text-[var(--muted)]">Triage:</span>
                  <Badge level={msg.meta.triage.level} />
                  {msg.meta.triage.score > 0 && <span className="text-xs text-[var(--muted)]">Score: {msg.meta.triage.score}</span>}
                </div>
              )}
              {msg.meta?.triage?.action && (
                <p className="mt-1.5 text-xs text-[var(--muted)] italic">{msg.meta.triage.action}</p>
              )}
              {msg.meta?.triage?.risk_factors?.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {msg.meta.triage.risk_factors.map(rf => (
                    <span key={rf} className="text-xs bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-900 px-2 py-0.5 rounded-full">⚠ {rf}</span>
                  ))}
                </div>
              )}
              <p className="text-[10px] opacity-30 mt-2 text-right">{timeAgo(msg.timestamp)}</p>
            </div>
            {msg.role === 'user' && (
              <div className="w-7 h-7 rounded-xl bg-[var(--forest)]/20 flex items-center justify-center text-sm flex-shrink-0 mt-0.5">👤</div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-2.5">
            <div className={`w-7 h-7 rounded-xl bg-gradient-to-br ${mode.grad} flex items-center justify-center text-xs flex-shrink-0`}>{mode.emoji}</div>
            <div className="bubble-ai dark:bg-[#1a2420] px-4 py-3 shadow-sm flex items-center gap-1.5">
              {[0, 0.15, 0.3].map(d => <div key={d} className="w-1.5 h-1.5 rounded-full bg-[var(--forest-light)] dark:bg-emerald-500 bounce-dot" style={{ animationDelay: `${d}s` }} />)}
              <span className="text-xs text-[var(--muted)] ml-1">Analyzing…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 pb-4 pt-3 border-t border-[var(--border)] bg-[var(--warm-white)] dark:bg-[#111815] flex-shrink-0">
        <p className="text-[10px] text-center text-[var(--muted)] mb-2.5 opacity-70">⚠ AI guidance only — always consult a licensed healthcare professional for medical decisions</p>

        {/* File preview pill */}
        {pendingFile && (
          <div className="flex items-center gap-2.5 mb-2.5 px-3 py-2 bg-[var(--mint)] dark:bg-[#1e3028] border border-[var(--sage)] border-opacity-40 rounded-xl anim-up">
            {pendingFile.preview
              ? <img src={pendingFile.preview} className="w-10 h-10 rounded-lg object-cover flex-shrink-0 border border-white/20" alt="preview" />
              : <div className="w-10 h-10 rounded-lg bg-[var(--forest)]/20 flex items-center justify-center text-xl flex-shrink-0">📄</div>
            }
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-[var(--forest)] dark:text-emerald-300 truncate">{pendingFile.file.name}</p>
              <p className="text-[10px] text-[var(--muted)]">
                {pendingFile.type === 'image' ? '🖼 Image' : '📄 PDF'} · {(pendingFile.file.size / 1024).toFixed(0)}KB
                {pendingFile.type === 'image' ? ' · Claude will analyze this image' : ' · Claude will read this document'}
              </p>
            </div>
            <button onClick={removePendingFile} className="text-[var(--muted)] hover:text-red-400 transition-colors p-1 flex-shrink-0 text-lg leading-none">×</button>
          </div>
        )}

        <div className="flex gap-2 items-end">
          {/* Hidden file input */}
          <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp,image/gif,application/pdf"
            onChange={pickFile} className="hidden" />

          {/* Upload button */}
          <button onClick={() => fileRef.current?.click()} disabled={loading}
            title="Upload image or PDF"
            className="w-11 h-11 rounded-xl border border-[var(--border)] hover:border-[var(--forest-light)] hover:bg-[var(--mint)] dark:hover:bg-[#1e3028] text-[var(--muted)] hover:text-[var(--forest)] dark:hover:text-emerald-400 flex items-center justify-center flex-shrink-0 transition-all disabled:opacity-40">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          </button>

          <textarea ref={inputRef} value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder={pendingFile ? `Ask something about this ${pendingFile.type}… (optional)` : `Message ${mode.label} assistant… (Enter to send)`}
            rows={1} style={{ lineHeight: '1.6', minHeight: '46px', maxHeight: '128px' }}
            className="flex-1 resize-none rounded-xl border border-[var(--border)] bg-[var(--cream)] dark:bg-[#161d1a] text-[var(--ink)] placeholder:text-[var(--muted)] placeholder:opacity-50 px-4 py-2.5 text-sm focus-forest overflow-y-auto transition-colors"
          />
          <button onClick={send} disabled={loading || (!input.trim() && !pendingFile)}
            className="w-11 h-11 rounded-xl bg-[var(--forest)] hover:bg-[var(--forest-mid)] disabled:opacity-40 text-white flex items-center justify-center flex-shrink-0 transition-all active:scale-95 shadow-sm">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z" /></svg>
          </button>
        </div>
      </div>
    </div>
  )
}

// ── APPOINTMENTS PANEL ────────────────────────────────────────────────────────
function AppointmentsPanel() {
  const [apts, setApts] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [sending, setSending] = useState(null)
  const [form, setForm] = useState({ title: '', doctor_name: '', clinic: '', location: '', scheduled_at: '', duration_mins: 30, notes: '', email: '', phone: '' })
  const U = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const load = () => API.getAppointments('demo_user').then(setApts).catch(() => {})
  useEffect(() => { load() }, [])

  const save = async () => {
    if (!form.title || !form.scheduled_at) return
    await API.bookAppointment({ ...form, user_id: 'demo_user' })
    setShowForm(false); setForm({ title: '', doctor_name: '', clinic: '', location: '', scheduled_at: '', duration_mins: 30, notes: '', email: '', phone: '' }); load()
  }
  const cancel = async id => { if (confirm('Cancel this appointment?')) { await API.cancelAppt(id); load() } }
  const remind = async (id, channels) => {
    setSending(`${id}-${channels.join('')}`)
    try {
      const r = await API.sendReminder(id, channels)
      const msgs = Object.entries(r.results || {}).map(([ch, res]) => `${ch}: ${res.success ? '✅ Sent' + (res.simulated ? ' (simulated)' : '') : '❌ ' + res.message}`)
      alert(msgs.join('\n') || '✅ Done')
    } catch (e) { alert('Error: ' + e.message) } finally { setSending(null) }
  }

  const STATUS = { upcoming: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-400 dark:border-emerald-900', completed: 'bg-stone-100 text-stone-500 border-stone-200 dark:bg-stone-800 dark:text-stone-400 dark:border-stone-700', cancelled: 'bg-red-50 text-red-500 border-red-200 dark:bg-red-950/30 dark:text-red-400 dark:border-red-900' }

  return (
    <div className="p-6 max-w-3xl space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h2 className="font-display font-bold text-2xl text-[var(--ink)]">📅 Appointments</h2>
          <p className="text-sm text-[var(--muted)] mt-0.5">Schedule, manage, and send reminders via email or WhatsApp</p>
        </div>
        <Btn onClick={() => setShowForm(true)}>+ Book Appointment</Btn>
      </div>

      {/* Empty */}
      {apts.length === 0 && !showForm && (
        <Card className="p-12 text-center">
          <p className="text-4xl mb-3">📅</p>
          <p className="font-semibold text-[var(--ink)]">No appointments yet</p>
          <p className="text-sm text-[var(--muted)] mt-1">Book your first doctor appointment to get started</p>
          <Btn className="mt-4" onClick={() => setShowForm(true)}>Book Now</Btn>
        </Card>
      )}

      {/* Appointment cards */}
      <div className="space-y-3">
        {apts.map(apt => (
          <Card key={apt.id} className="p-5 anim-up">
            <div className="flex gap-4 flex-wrap">
              {/* Left: info */}
              <div className="flex items-start gap-3 flex-1 min-w-0">
                <div className="w-12 h-12 rounded-2xl bg-[var(--mint)] dark:bg-[#1e3028] flex items-center justify-center text-2xl flex-shrink-0">📅</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-display font-bold text-[var(--ink)]">{apt.title}</p>
                    <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${STATUS[apt.status] || STATUS.upcoming}`}>{apt.status}</span>
                  </div>
                  <div className="mt-2 space-y-0.5 text-sm">
                    {apt.doctor_name && <p className="text-[var(--muted)]">👨‍⚕️ {apt.doctor_name}{apt.clinic ? ` · ${apt.clinic}` : ''}</p>}
                    <p className="font-semibold text-[var(--forest)] dark:text-emerald-400">🕐 {fmtDateTime(apt.scheduled_at)}</p>
                    {apt.location && <p className="text-[var(--muted)] text-xs">📍 {apt.location}</p>}
                    {apt.notes && <p className="text-[var(--muted)] text-xs italic">📝 {apt.notes}</p>}
                  </div>
                  {(apt.email || apt.phone) && (
                    <div className="flex gap-3 mt-2 text-xs text-[var(--muted)]">
                      {apt.email && <span className="flex items-center gap-1">✉️ {apt.email}</span>}
                      {apt.phone && <span className="flex items-center gap-1">📱 {apt.phone}</span>}
                    </div>
                  )}
                </div>
              </div>
              {/* Right: actions */}
              {apt.status === 'upcoming' && (
                <div className="flex flex-col gap-1.5 flex-shrink-0">
                  {apt.email && (
                    <Btn v="soft" sm onClick={() => remind(apt.id, ['email'])} disabled={!!sending}>
                      {sending?.startsWith(apt.id) ? '⏳' : '✉️'} Email Reminder
                    </Btn>
                  )}
                  {apt.phone && (
                    <Btn v="soft" sm onClick={() => remind(apt.id, ['whatsapp'])} disabled={!!sending}>
                      {sending?.startsWith(apt.id) ? '⏳' : '💬'} WhatsApp
                    </Btn>
                  )}
                  {apt.email && apt.phone && (
                    <Btn v="soft" sm onClick={() => remind(apt.id, ['email', 'whatsapp'])} disabled={!!sending}>
                      📣 Send Both
                    </Btn>
                  )}
                  <Btn v="ghost" sm onClick={() => cancel(apt.id)} className="text-red-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/20">
                    Cancel
                  </Btn>
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>

      {/* Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={e => e.target === e.currentTarget && setShowForm(false)}>
          <Card className="w-full max-w-lg p-6 space-y-4 shadow-2xl max-h-[90vh] overflow-y-auto anim-up">
            <div className="flex items-center justify-between">
              <h3 className="font-display font-bold text-xl text-[var(--ink)]">Book Appointment</h3>
              <button onClick={() => setShowForm(false)} className="w-8 h-8 rounded-full hover:bg-[var(--border)] flex items-center justify-center text-[var(--muted)] text-lg">×</button>
            </div>
            <Input label="Appointment title *" value={form.title} onChange={e => U('title', e.target.value)} placeholder="e.g. Cardiology Checkup" />
            <div className="grid grid-cols-2 gap-3">
              <Input label="Doctor name" value={form.doctor_name} onChange={e => U('doctor_name', e.target.value)} placeholder="Dr. Smith" />
              <Input label="Clinic / Hospital" value={form.clinic} onChange={e => U('clinic', e.target.value)} placeholder="City Hospital" />
            </div>
            <Input label="Location / Address" value={form.location} onChange={e => U('location', e.target.value)} placeholder="123 Main St" />
            <div className="grid grid-cols-2 gap-3">
              <Input label="Date & Time *" type="datetime-local" value={form.scheduled_at} onChange={e => U('scheduled_at', e.target.value)} />
              <Input label="Duration (mins)" type="number" value={form.duration_mins} onChange={e => U('duration_mins', +e.target.value)} min={5} max={240} />
            </div>
            <Input label="Notes / Instructions" value={form.notes} onChange={e => U('notes', e.target.value)} placeholder="Bring insurance, fasting required..." />
            <div className="pt-1 border-t border-[var(--border)]">
              <p className="text-xs font-semibold text-[var(--muted)] uppercase tracking-widest mb-3">Notification contacts (for reminders)</p>
              <div className="grid grid-cols-2 gap-3">
                <Input label="Email address" type="email" value={form.email} onChange={e => U('email', e.target.value)} placeholder="you@example.com" />
                <Input label="WhatsApp phone" value={form.phone} onChange={e => U('phone', e.target.value)} placeholder="+1234567890" />
              </div>
            </div>
            <div className="flex gap-2.5 pt-1">
              <Btn onClick={save} className="flex-1">Book Appointment</Btn>
              <Btn v="outline" onClick={() => setShowForm(false)}>Cancel</Btn>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}

// ── NOTIFICATIONS PANEL ───────────────────────────────────────────────────────
function NotificationsPanel() {
  const [email, setEmail] = useState(() => localStorage.getItem('ma-email') || '')
  const [phone, setPhone] = useState(() => localStorage.getItem('ma-phone') || '')
  const [loading, setLoading] = useState('')
  const [result, setResult] = useState(null)

  const saveContacts = () => { localStorage.setItem('ma-email', email); localStorage.setItem('ma-phone', phone); alert('✅ Contacts saved!') }

  const run = async (fn, key) => {
    setLoading(key); setResult(null)
    try { setResult(await fn()) }
    catch (e) { setResult({ success: false, message: e.message }) }
    finally { setLoading('') }
  }

  const testEmail    = () => { if (!email) return alert('Enter email first'); run(() => API.testNotif({ channel: 'email', to: email }), 'test-email') }
  const testWA       = () => { if (!phone) return alert('Enter phone first'); run(() => API.testNotif({ channel: 'whatsapp', to: phone }), 'test-wa') }
  const medEmail     = () => { if (!email) return alert('Enter email first'); run(() => API.sendMedReminder({ user_id: 'demo_user', channels: ['email'], email }), 'med-email') }
  const medWA        = () => { if (!phone) return alert('Enter phone first'); run(() => API.sendMedReminder({ user_id: 'demo_user', channels: ['whatsapp'], phone }), 'med-wa') }
  const reportEmail  = () => { if (!email) return alert('Enter email first'); run(() => API.sendAdherenceRpt({ user_id: 'demo_user', channels: ['email'], email, days: 7, include_pdf: true }), 'rpt-email') }
  const reportWA     = () => { if (!phone) return alert('Enter phone first'); run(() => API.sendAdherenceRpt({ user_id: 'demo_user', channels: ['whatsapp'], phone, days: 7 }), 'rpt-wa') }

  const ResultBox = ({ r }) => {
    if (!r) return null
    const cls = r.success !== false ? 'notif-success' : r.simulated ? 'notif-sim' : 'notif-fail'
    return (
      <div className={`mt-4 p-3.5 rounded-xl flex items-start gap-2.5 text-sm anim-up ${cls}`}>
        <span className="flex-shrink-0 text-base">{r.success !== false ? (r.simulated ? '🟡' : '✅') : '❌'}</span>
        <div>
          <p className="font-semibold">{r.success !== false ? (r.simulated ? 'Simulated (credentials not configured)' : 'Sent successfully!') : 'Failed'}</p>
          <p className="text-xs mt-0.5 opacity-80">{r.message || JSON.stringify(r.results || r)}</p>
          {r.simulated && <p className="text-xs mt-1.5 opacity-70">Configure SMTP / Twilio credentials to send real messages. See the Setup Guide below.</p>}
        </div>
      </div>
    )
  }

  const Section = ({ title, children }) => (
    <Card className="p-5 space-y-4">
      <h3 className="font-display font-semibold text-[var(--ink)]">{title}</h3>
      {children}
    </Card>
  )

  return (
    <div className="p-6 max-w-2xl space-y-5">
      <div>
        <h2 className="font-display font-bold text-2xl text-[var(--ink)]">🔔 Notifications</h2>
        <p className="text-sm text-[var(--muted)] mt-0.5">Email & WhatsApp alerts for medications, appointments, and reports</p>
      </div>

      {/* Contacts */}
      <Section title="📬 Your Contact Details">
        <div className="space-y-3">
          <Input label="Email address" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" />
          <Input label="WhatsApp phone number" value={phone} onChange={e => setPhone(e.target.value)} placeholder="+1234567890 (include country code)" />
        </div>
        <Btn onClick={saveContacts} className="w-full">💾 Save Contacts</Btn>
      </Section>

      {/* Test */}
      <Section title="🧪 Send a Test Message">
        <p className="text-xs text-[var(--muted)]">Verify your setup. If credentials aren't configured, you'll see a simulated response instead.</p>
        <div className="grid grid-cols-2 gap-2.5">
          <Btn v="soft" onClick={testEmail} disabled={!!loading}>
            {loading === 'test-email' ? '⏳' : '✉️'} Test Email
          </Btn>
          <Btn v="soft" onClick={testWA} disabled={!!loading}>
            {loading === 'test-wa' ? '⏳' : '💬'} Test WhatsApp
          </Btn>
        </div>
        <ResultBox r={result} />
      </Section>

      {/* Medication reminders */}
      <Section title="💊 Medication Dose Reminders">
        <p className="text-xs text-[var(--muted)]">Send today's pending medication schedule as a reminder right now.</p>
        <div className="grid grid-cols-2 gap-2.5">
          <Btn v="soft" onClick={medEmail} disabled={!!loading}>
            {loading === 'med-email' ? '⏳' : '✉️'} Email Reminder
          </Btn>
          <Btn v="soft" onClick={medWA} disabled={!!loading}>
            {loading === 'med-wa' ? '⏳' : '💬'} WhatsApp Reminder
          </Btn>
        </div>
        <ResultBox r={result} />
      </Section>

      {/* Adherence report */}
      <Section title="📊 Weekly Adherence Report">
        <p className="text-xs text-[var(--muted)]">Send a 7-day summary of your medication adherence. Email includes a PDF attachment.</p>
        <div className="grid grid-cols-2 gap-2.5">
          <Btn v="soft" onClick={reportEmail} disabled={!!loading}>
            {loading === 'rpt-email' ? '⏳' : '📄'} Email + PDF
          </Btn>
          <Btn v="soft" onClick={reportWA} disabled={!!loading}>
            {loading === 'rpt-wa' ? '⏳' : '💬'} WhatsApp Summary
          </Btn>
        </div>
        <ResultBox r={result} />
      </Section>

      {/* Auto-schedule info */}
      <Card className="p-5 bg-[var(--mint)] dark:bg-[#1a2e24] border-[var(--sage)] border-opacity-30 space-y-2">
        <p className="font-display font-semibold text-[var(--forest)] dark:text-emerald-300 text-sm">⏰ Automatic Scheduled Reminders</p>
        <p className="text-xs text-[var(--muted)]">When <code className="bg-black/10 dark:bg-white/10 px-1 rounded">REMINDER_EMAIL</code> and <code className="bg-black/10 dark:bg-white/10 px-1 rounded">REMINDER_PHONE</code> are set in your <code className="bg-black/10 dark:bg-white/10 px-1 rounded">.env</code>, the background scheduler automatically sends:</p>
        <ul className="text-xs text-[var(--muted)] space-y-1 ml-2">
          <li>⏰ <strong>Daily at 7 AM UTC</strong> — today's medication schedule</li>
          <li>📅 <strong>24h before appointments</strong> — appointment reminders</li>
          <li>📊 <strong>Every Monday 8 AM</strong> — weekly adherence report with PDF</li>
        </ul>
      </Card>

      {/* Setup guide */}
      <Card className="p-5 space-y-4">
        <h3 className="font-display font-semibold text-[var(--ink)]">⚙️ Configuration Guide</h3>
        <div className="space-y-4 text-sm">
          <div>
            <p className="font-semibold text-[var(--ink)] mb-1.5">✉️ Email — Gmail SMTP (free)</p>
            <pre className="bg-[var(--ink)] text-emerald-400 text-xs rounded-xl p-4 overflow-x-auto font-mono leading-relaxed">{`SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=xxxx xxxx xxxx xxxx  # App Password`}</pre>
            <p className="text-xs text-[var(--muted)] mt-1.5">Generate App Password: <span className="text-[var(--forest)] dark:text-emerald-400">myaccount.google.com/apppasswords</span></p>
          </div>
          <div>
            <p className="font-semibold text-[var(--ink)] mb-1.5">💬 WhatsApp — Twilio Sandbox (free)</p>
            <pre className="bg-[var(--ink)] text-emerald-400 text-xs rounded-xl p-4 overflow-x-auto font-mono leading-relaxed">{`TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886`}</pre>
            <p className="text-xs text-[var(--muted)] mt-1.5">Sign up free → <span className="text-[var(--forest)] dark:text-emerald-400">twilio.com</span> → Messaging → WhatsApp Sandbox<br />Then text <strong>join &lt;word&gt;</strong> to +1 415 523 8886 from your WhatsApp to activate</p>
          </div>
        </div>
      </Card>
    </div>
  )
}

// ── WEB SEARCH AGENT ──────────────────────────────────────────────────────────
function SearchAgent() {
  const [tab, setTab] = useState('drug')
  const [query, setQuery] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const search = async () => {
    if (!query.trim()) return
    setLoading(true); setResult(null)
    try {
      if (tab === 'drug')       setResult(await API.searchDrug(query))
      else if (tab === 'news')  setResult(await API.searchNews(query))
      else                      setResult(await API.findSpecialists(query))
    } catch (e) { setResult({ error: e.response?.data?.detail || e.message }) }
    finally { setLoading(false) }
  }

  const TABS = [['drug', '🔬', 'Drug Search'], ['news', '📰', 'Medical News'], ['specialist', '👨‍⚕️', 'Find Specialist']]
  const PH   = { drug: 'e.g. metformin, warfarin, amoxicillin', news: 'e.g. drug safety, new vaccines, clinical trials', specialist: 'Describe your symptoms...' }

  const ResultCard = ({ r }) => (
    <Card className="p-4 hover:border-[var(--forest-light)] transition-colors">
      <a href={r.url} target="_blank" rel="noopener noreferrer" className="block">
        <p className="font-semibold text-sm text-[var(--forest)] dark:text-emerald-400 hover:underline">{r.title}</p>
        <p className="text-xs text-[var(--muted)] mt-1.5 leading-relaxed">{r.snippet?.slice(0, 220)}</p>
        <p className="text-[10px] text-[var(--muted)] mt-2 flex items-center gap-1">
          <span className="w-3.5 h-3.5 rounded bg-[var(--border)] flex items-center justify-center text-[8px]">🔗</span>
          {r.source}
        </p>
      </a>
    </Card>
  )

  return (
    <div className="p-6 max-w-2xl space-y-5">
      <div>
        <h2 className="font-display font-bold text-2xl text-[var(--ink)]">🌐 Web Search Agent</h2>
        <p className="text-sm text-[var(--muted)] mt-0.5">Live drug info from DuckDuckGo + PubMed, summarized by AI</p>
      </div>

      {/* Tab switcher */}
      <div className="flex bg-[var(--mint)] dark:bg-[#1a2e24] rounded-xl p-1 gap-1">
        {TABS.map(([id, emoji, label]) => (
          <button key={id} onClick={() => { setTab(id); setResult(null); setQuery('') }}
            className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all flex items-center justify-center gap-1.5 ${tab === id ? 'bg-[var(--warm-white)] dark:bg-[#1e2a24] shadow text-[var(--forest)] dark:text-emerald-300' : 'text-[var(--muted)]'}`}>
            {emoji} {label}
          </button>
        ))}
      </div>

      {/* Search bar */}
      <div className="flex gap-2.5">
        <input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && search()}
          placeholder={PH[tab]}
          className="flex-1 rounded-xl border border-[var(--border)] bg-[var(--warm-white)] dark:bg-[#1a2420] text-[var(--ink)] placeholder:text-[var(--muted)] placeholder:opacity-60 px-4 py-2.5 text-sm focus-forest" />
        <Btn onClick={search} disabled={loading}>{loading ? '⏳ Searching…' : '🔍 Search'}</Btn>
      </div>

      {result?.error && (
        <Card className="p-4 border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/20">
          <p className="text-sm text-red-600 dark:text-red-400">⚠️ {result.error}</p>
        </Card>
      )}

      {result && !result.error && (
        <div className="space-y-4 anim-up">
          {/* AI Summary */}
          {result.ai_summary && (
            <Card className="p-5 bg-gradient-to-br from-[var(--mint)] to-transparent dark:from-[#1e2e24] dark:to-[#1a2420]">
              <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)] mb-2.5">✨ AI Summary</p>
              <MsgBody text={result.ai_summary} />
            </Card>
          )}
          {/* Explanation (specialists) */}
          {result.explanation && (
            <Card className="p-5">
              <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)] mb-2.5">💡 Analysis</p>
              <MsgBody text={result.explanation} />
              {result.note && <p className="text-xs text-[var(--muted)] italic mt-2.5 border-t border-[var(--border)] pt-2.5">{result.note}</p>}
            </Card>
          )}
          {/* Specialist pills */}
          {result.suggested_specialists?.length > 0 && (
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)] mb-2">Recommended Specialists</p>
              <div className="flex flex-wrap gap-2">
                {result.suggested_specialists.map(s => (
                  <span key={s} className="bg-[var(--mint)] dark:bg-[#1e3028] text-[var(--forest)] dark:text-emerald-300 border border-[var(--sage)] border-opacity-40 px-3.5 py-1.5 rounded-full text-sm font-medium">👨‍⚕️ {s}</span>
                ))}
              </div>
            </div>
          )}
          {/* Web results */}
          {(result.web_results || result.news || []).length > 0 && (
            <div className="space-y-2.5">
              <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)]">Web Results</p>
              {(result.web_results || result.news).slice(0, 5).map((r, i) => <ResultCard key={i} r={r} />)}
            </div>
          )}
          {/* PubMed */}
          {(result.pubmed_results || result.research || []).length > 0 && (
            <div className="space-y-2.5">
              <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)]">📚 PubMed Research</p>
              {(result.pubmed_results || result.research).map((r, i) => <ResultCard key={i} r={r} />)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── DRUG CHECKER ──────────────────────────────────────────────────────────────
function DrugChecker() {
  const [inp, setInp] = useState(''); const [drugs, setDrugs] = useState([]); const [res, setRes] = useState(null); const [loading, setLoading] = useState(false)
  const add = () => { const d = inp.trim().toLowerCase(); if (!d || drugs.includes(d)) return; setDrugs(p => [...p, d]); setInp('') }
  const check = async () => { setLoading(true); setRes(null); try { setRes(await API.checkInteraction(drugs)) } catch { } finally { setLoading(false) }  }
  return (
    <div className="p-6 max-w-2xl space-y-5">
      <div><h2 className="font-display font-bold text-2xl text-[var(--ink)]">💊 Drug Interaction Checker</h2><p className="text-sm text-[var(--muted)] mt-0.5">Check interactions between multiple medications</p></div>
      <div className="flex gap-2.5">
        <input value={inp} onChange={e => setInp(e.target.value)} onKeyDown={e => e.key === 'Enter' && add()} placeholder="Type a drug name and press Enter…" className="flex-1 rounded-xl border border-[var(--border)] bg-[var(--warm-white)] dark:bg-[#1a2420] text-[var(--ink)] placeholder:text-[var(--muted)] placeholder:opacity-60 px-4 py-2.5 text-sm focus-forest" />
        <Btn onClick={add}>+ Add</Btn>
      </div>
      {drugs.length > 0 && <div className="flex flex-wrap gap-2">{drugs.map(d => <span key={d} className="flex items-center gap-2 bg-[var(--mint)] dark:bg-[#1e3028] text-[var(--forest)] dark:text-emerald-300 px-3.5 py-1.5 rounded-full text-sm border border-[var(--sage)] border-opacity-30">💊 {d}<button onClick={() => setDrugs(p => p.filter(x => x !== d))} className="text-[var(--muted)] hover:text-red-500 transition-colors text-lg leading-none">×</button></span>)}</div>}
      <Btn onClick={check} disabled={loading || drugs.length < 2}>{loading ? '⏳ Checking…' : '🔍 Check Interactions'}</Btn>
      {res && <div className="space-y-3 anim-up">
        <Card className="p-4 flex items-center gap-3"><span className="text-sm text-[var(--muted)]">Overall Risk:</span><Badge level={res.overall_risk} /></Card>
        {res.interactions?.map((item, i) => <Card key={i} className="p-4"><div className="flex items-center justify-between mb-2.5 flex-wrap gap-2"><code className="text-xs bg-[var(--border)] px-2.5 py-1 rounded-lg">{item.pair[0]} + {item.pair[1]}</code><Badge level={item.risk_level} /></div>{item.interactions?.length > 0 ? item.interactions.map((n, j) => <p key={j} className="text-xs text-[var(--muted)] mt-1">› {n}</p>) : <p className="text-xs text-[var(--muted)] italic">No significant interaction found</p>}</Card>)}
        {res.response && <Card className="p-4"><p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)] mb-2.5">AI Analysis</p><MsgBody text={res.response} /></Card>}
      </div>}
    </div>
  )
}

// ── MEDICINE INFO ─────────────────────────────────────────────────────────────
function MedicineInfo() {
  const [q, setQ] = useState(''); const [res, setRes] = useState(null); const [loading, setLoading] = useState(false)
  const search = async () => { if (!q.trim()) return; setLoading(true); setRes(null); try { setRes(await API.getMedicineInfo(q)) } catch { setRes({ error: true }) } finally { setLoading(false) } }
  return (
    <div className="p-6 max-w-2xl space-y-5">
      <div><h2 className="font-display font-bold text-2xl text-[var(--ink)]">🔬 Medicine Information</h2><p className="text-sm text-[var(--muted)] mt-0.5">FDA drug database lookup with AI-powered summary</p></div>
      <div className="flex gap-2.5"><input value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => e.key === 'Enter' && search()} placeholder="Search any drug e.g. ibuprofen, metformin, aspirin…" className="flex-1 rounded-xl border border-[var(--border)] bg-[var(--warm-white)] dark:bg-[#1a2420] text-[var(--ink)] placeholder:text-[var(--muted)] placeholder:opacity-60 px-4 py-2.5 text-sm focus-forest" /><Btn onClick={search} disabled={loading}>{loading ? '⏳' : '🔍 Search'}</Btn></div>
      {res?.error && <Card className="p-4 border-red-200 dark:border-red-900"><p className="text-sm text-red-500">Drug not found. Try the generic name (e.g. "acetaminophen" instead of "Tylenol")</p></Card>}
      {res && !res.error && <div className="space-y-3 anim-up">
        <Card className="p-5 bg-gradient-to-br from-[var(--mint)] to-transparent dark:from-[#1e3028] dark:to-[#1a2420]"><h3 className="font-display font-bold text-xl capitalize text-[var(--ink)]">{res.name}</h3>{res.brand_names?.length > 0 && <p className="text-sm text-[var(--muted)] mt-1">Also sold as: {res.brand_names.join(', ')}</p>}{res.rxcui && <p className="text-xs font-mono text-[var(--muted)] mt-0.5 opacity-60">RxNorm: {res.rxcui}</p>}</Card>
        {res.ai_summary && <Card className="p-5"><p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)] mb-2.5">✨ AI Summary</p><MsgBody text={res.ai_summary} /></Card>}
        {[['📋 Indications', res.indications], ['💉 Dosage', res.dosage], ['⚠️ Warnings', res.warnings], ['😣 Side Effects', res.side_effects], ['🚫 Contraindications', res.contraindications]].map(([t, c]) => c ? <Card key={t} className="p-4"><p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)] mb-2">{t}</p><p className="text-sm text-[var(--ink)] leading-relaxed opacity-80">{c}</p></Card> : null)}
      </div>}
    </div>
  )
}

// ── MED TRACKER ───────────────────────────────────────────────────────────────
function MedTracker() {
  const [meds, setMeds] = useState([]); const [schedule, setSchedule] = useState([]); const [adherence, setAdherence] = useState(null); const [tab, setTab] = useState('today'); const [showAdd, setShowAdd] = useState(false); const [exporting, setExporting] = useState(false)
  const [form, setForm] = useState({ name: '', dosage: '', frequency: 'once_daily', times: ['08:00'], notes: '' })
  const U = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const load = () => Promise.all([API.getMedications('demo_user'), API.getSchedule('demo_user'), API.getAdherence('demo_user', 30)]).then(([m, s, a]) => { setMeds(m); setSchedule(s); setAdherence(a) })
  useEffect(() => { load() }, [])
  const addMed = async () => { if (!form.name.trim()) return; await API.addMedication({ ...form, user_id: 'demo_user' }); setShowAdd(false); load() }
  const logD = async (mid, status) => { await API.logDose(mid, { user_id: 'demo_user', status }); load() }
  const delMed = async id => { if (!confirm('Remove?')) return; await API.deleteMedication(id); load() }
  const exportPdf = async () => { setExporting(true); try { dlBlob(await API.exportAdherence('demo_user'), 'adherence-report.pdf') } catch { alert('Error: pip install reportlab') } finally { setExporting(false) } }
  const overall = adherence?.overall_adherence ?? 0
  const barC = overall >= 80 ? 'bg-emerald-500' : overall >= 50 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="p-6 max-w-2xl space-y-5">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div><h2 className="font-display font-bold text-2xl text-[var(--ink)]">💉 Medication Tracker</h2><p className="text-sm text-[var(--muted)] mt-0.5">Track doses, view adherence, export reports</p></div>
        <div className="flex gap-2"><Btn v="soft" sm onClick={exportPdf} disabled={exporting}>📄 {exporting ? '…' : 'Export PDF'}</Btn><Btn sm onClick={() => setShowAdd(true)}>+ Add Med</Btn></div>
      </div>
      {adherence && <Card className="p-5"><div className="flex items-center justify-between mb-3"><span className="text-sm font-medium text-[var(--muted)]">30-day adherence</span><span className={`text-2xl font-display font-bold ${overall >= 80 ? 'text-emerald-500' : overall >= 50 ? 'text-amber-500' : 'text-red-500'}`}>{overall}%</span></div><div className="h-2.5 bg-[var(--border)] rounded-full overflow-hidden"><div className={`h-full ${barC} rounded-full transition-all duration-700`} style={{ width: `${overall}%` }} /></div><p className="text-xs text-[var(--muted)] mt-2">{overall >= 80 ? '✅ Excellent adherence — keep it up!' : overall >= 50 ? '⚠️ Fair adherence — set reminders to improve' : '❗ Low adherence — consider setting up WhatsApp reminders'}</p></Card>}
      <div className="flex bg-[var(--mint)] dark:bg-[#1e2e26] rounded-xl p-1 gap-1">{[['today', '📅 Today'], ['meds', '💊 Medications']].map(([id, l]) => <button key={id} onClick={() => setTab(id)} className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${tab === id ? 'bg-[var(--warm-white)] dark:bg-[#1e2a24] shadow text-[var(--forest)] dark:text-emerald-300' : 'text-[var(--muted)]'}`}>{l}</button>)}</div>
      {tab === 'today' && <div className="space-y-2">{schedule.length === 0 && <Card className="p-10 text-center"><p className="text-3xl mb-2">📅</p><p className="text-sm text-[var(--muted)]">No medications scheduled today. Add medications using the button above.</p></Card>}{schedule.map((item, i) => <Card key={i} className={`p-4 flex items-center gap-3 transition-opacity ${item.taken ? 'opacity-60' : ''}`}><div className={`w-10 h-10 rounded-full flex items-center justify-center text-xl flex-shrink-0 ${item.taken ? 'bg-emerald-100 dark:bg-emerald-900/20' : 'bg-[var(--mint)] dark:bg-[#1e3028]'}`}>{item.taken ? '✅' : '⏰'}</div><div className="flex-1 min-w-0"><p className={`font-semibold text-sm ${item.taken ? 'line-through text-[var(--muted)]' : 'text-[var(--ink)]'}`}>{item.name} <span className="font-normal text-[var(--muted)] text-xs">{item.dosage}</span></p><p className="text-xs text-[var(--muted)] mt-0.5">🕐 {item.time}</p></div>{!item.taken && <div className="flex gap-1.5"><Btn v="soft" sm onClick={() => logD(item.medication_id, 'taken')}>✓ Taken</Btn><Btn v="ghost" sm onClick={() => logD(item.medication_id, 'skipped')}>Skip</Btn></div>}</Card>)}</div>}
      {tab === 'meds' && <div className="space-y-2">{meds.length === 0 && <Card className="p-10 text-center"><p className="text-3xl mb-2">💊</p><p className="text-sm text-[var(--muted)]">No medications added yet.</p></Card>}{meds.map(med => { const ms = adherence?.medications?.find(m => m.medication_id === med.id); return <Card key={med.id} className="p-4 flex items-center gap-3"><div className="w-10 h-10 rounded-xl bg-[var(--mint)] dark:bg-[#1e3028] flex items-center justify-center text-xl flex-shrink-0">💊</div><div className="flex-1 min-w-0"><p className="font-semibold text-[var(--ink)]">{med.name} <span className="text-xs font-normal text-[var(--muted)]">{med.dosage}</span></p><p className="text-xs text-[var(--muted)]">{FREQ_LABELS[med.frequency] || med.frequency} · {(med.times || []).join(', ')}</p>{ms && <div className="flex items-center gap-2 mt-1.5"><div className="flex-1 h-1.5 bg-[var(--border)] rounded-full overflow-hidden"><div className={`h-full rounded-full ${ms.adherence_pct >= 80 ? 'bg-emerald-500' : ms.adherence_pct >= 50 ? 'bg-amber-500' : 'bg-red-500'}`} style={{ width: `${ms.adherence_pct}%` }} /></div><span className={`text-xs font-bold ${ms.adherence_pct >= 80 ? 'text-emerald-500' : ms.adherence_pct >= 50 ? 'text-amber-500' : 'text-red-500'}`}>{ms.adherence_pct}%</span></div>}</div><button onClick={() => delMed(med.id)} className="text-[var(--border)] hover:text-red-400 transition-colors p-1 flex-shrink-0"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" /></svg></button></Card> })}</div>}
      {showAdd && <div className="fixed inset-0 bg-black/50 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={e => e.target === e.currentTarget && setShowAdd(false)}><Card className="w-full max-w-md p-6 space-y-4 shadow-2xl anim-up"><div className="flex items-center justify-between"><h3 className="font-display font-bold text-xl text-[var(--ink)]">Add Medication</h3><button onClick={() => setShowAdd(false)} className="w-8 h-8 rounded-full hover:bg-[var(--border)] flex items-center justify-center text-[var(--muted)]">×</button></div><Input label="Drug name *" value={form.name} onChange={e => U('name', e.target.value)} placeholder="e.g. Ibuprofen" /><div className="grid grid-cols-2 gap-3"><Input label="Dosage" value={form.dosage} onChange={e => U('dosage', e.target.value)} placeholder="400mg" /><Select label="Frequency" value={form.frequency} onChange={e => U('frequency', e.target.value)}>{Object.entries(FREQ_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select></div><Input label="Times (comma separated)" value={form.times.join(', ')} onChange={e => U('times', e.target.value.split(',').map(t => t.trim()).filter(Boolean))} placeholder="08:00, 20:00" /><Input label="Notes" value={form.notes} onChange={e => U('notes', e.target.value)} placeholder="Take with food" /><div className="flex gap-2.5 pt-1"><Btn onClick={addMed} className="flex-1">Add Medication</Btn><Btn v="outline" onClick={() => setShowAdd(false)}>Cancel</Btn></div></Card></div>}
    </div>
  )
}

// ── BMI CALC ──────────────────────────────────────────────────────────────────
function BMICalc() {
  const [unit, setUnit] = useState('metric'); const [w, setW] = useState(''); const [h, setH] = useState(''); const [ft, setFt] = useState(''); const [inc, setInc] = useState(''); const [res, setRes] = useState(null)
  const calc = () => { let hm, wk; if (unit === 'metric') { hm = parseFloat(h) / 100; wk = parseFloat(w) } else { hm = (parseFloat(ft) * 12 + parseFloat(inc || 0)) * 0.0254; wk = parseFloat(w) * 0.453592 }; if (!hm || !wk || hm <= 0 || wk <= 0) return; const bmi = wk / (hm * hm); const cat = bmi < 18.5 ? ['Underweight', 'text-blue-500', 'Consider a balanced diet with adequate calories.'] : bmi < 25 ? ['Normal weight', 'text-emerald-500', 'Great! Maintain with regular exercise and balanced diet.'] : bmi < 30 ? ['Overweight', 'text-amber-500', 'Consider lifestyle changes and consult your GP.'] : ['Obese', 'text-red-500', 'Please consult a healthcare provider for support.']; setRes({ bmi: bmi.toFixed(1), cat: cat[0], col: cat[1], advice: cat[2] }) }
  const pct = res ? Math.min(95, Math.max(3, ((parseFloat(res.bmi) - 15) / 25) * 100)) : 50
  return (
    <div className="p-6 max-w-md space-y-5">
      <div><h2 className="font-display font-bold text-2xl text-[var(--ink)]">⚖️ BMI Calculator</h2><p className="text-sm text-[var(--muted)] mt-0.5">Body Mass Index calculator with health guidance</p></div>
      <div className="flex bg-[var(--mint)] dark:bg-[#1e2e26] rounded-xl p-1 gap-1">{['metric', 'imperial'].map(u => <button key={u} onClick={() => { setUnit(u); setRes(null) }} className={`flex-1 py-2 text-sm font-semibold rounded-lg capitalize transition-all ${unit === u ? 'bg-[var(--warm-white)] dark:bg-[#1e2a24] shadow text-[var(--forest)] dark:text-emerald-300' : 'text-[var(--muted)]'}`}>{u}</button>)}</div>
      <div className="grid grid-cols-2 gap-3"><Input label={`Weight (${unit === 'metric' ? 'kg' : 'lbs'})`} type="number" value={w} onChange={e => setW(e.target.value)} placeholder={unit === 'metric' ? '70' : '154'} />{unit === 'metric' ? <Input label="Height (cm)" type="number" value={h} onChange={e => setH(e.target.value)} placeholder="175" /> : <div><label className="block text-xs font-medium text-[var(--muted)] mb-1.5">Height</label><div className="flex gap-1.5"><input type="number" value={ft} onChange={e => setFt(e.target.value)} placeholder="5ft" className="w-1/2 rounded-xl border border-[var(--border)] bg-[var(--warm-white)] dark:bg-[#1a2420] text-[var(--ink)] px-3 py-2.5 text-sm focus-forest" /><input type="number" value={inc} onChange={e => setInc(e.target.value)} placeholder="9in" className="w-1/2 rounded-xl border border-[var(--border)] bg-[var(--warm-white)] dark:bg-[#1a2420] text-[var(--ink)] px-3 py-2.5 text-sm focus-forest" /></div></div>}</div>
      <Btn onClick={calc} className="w-full">Calculate BMI</Btn>
      {res && <Card className="p-6 space-y-5 anim-up"><div className="text-center"><p className="font-display font-bold text-6xl text-[var(--ink)]">{res.bmi}</p><p className={`font-semibold text-lg mt-1 ${res.col}`}>{res.cat}</p></div><div><div className="relative h-4 rounded-full overflow-hidden" style={{ background: 'linear-gradient(to right, #60a5fa, #34d399, #fbbf24, #f87171)' }}><div className="absolute inset-y-0 w-0.5 bg-[var(--ink)] dark:bg-white rounded-full transition-all duration-700" style={{ left: `${pct}%`, transform: 'translateX(-50%)' }} /></div><div className="flex justify-between text-[10px] text-[var(--muted)] mt-1 px-0.5"><span>15</span><span>18.5</span><span>25</span><span>30</span><span>40</span></div></div><p className="text-sm text-[var(--muted)] bg-[var(--mint)] dark:bg-[#1e3028] p-3.5 rounded-xl">💡 {res.advice}</p></Card>}
    </div>
  )
}

// ── SIDEBAR ───────────────────────────────────────────────────────────────────
function Sidebar({ sessions, activeId, onSelect, onNew, onDelete, onRename, collapsed, onToggle, dark, onToggleDark }) {
  const [editId, setEditId] = useState(null)
  const [editTitle, setEditTitle] = useState('')
  const startEdit = (s, e) => { e.stopPropagation(); setEditId(s.id); setEditTitle(s.title) }
  const saveEdit  = async id => { await onRename(id, editTitle); setEditId(null) }

  return (
    <div className={`flex flex-col h-full bg-[var(--warm-white)] dark:bg-[#0f1a15] border-r border-[var(--border)] transition-all duration-300 ${collapsed ? 'w-14' : 'w-64'} flex-shrink-0`}>
      {/* Logo */}
      <div className="flex items-center justify-between px-3 py-4 border-b border-[var(--border)] flex-shrink-0">
        {!collapsed ? (
          <>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[var(--forest-light)] to-[var(--forest)] flex items-center justify-center text-white font-bold text-sm shadow-sm">✚</div>
              <div>
                <p className="font-display font-bold text-sm text-[var(--ink)]">MediAgent</p>
                <p className="text-[10px] text-[var(--muted)]">v5.0 · AI Copilot</p>
              </div>
            </div>
            <button onClick={onToggle} className="text-[var(--muted)] hover:text-[var(--ink)] p-1 transition-colors">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="rotate-180"><path d="M9 18l6-6-6-6" /></svg>
            </button>
          </>
        ) : (
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[var(--forest-light)] to-[var(--forest)] flex items-center justify-center text-white font-bold text-sm mx-auto shadow-sm">✚</div>
        )}
      </div>

      {/* New chat */}
      <div className={`${collapsed ? 'py-2 flex flex-col items-center gap-1' : 'p-3'} border-b border-[var(--border)] flex-shrink-0`}>
        {!collapsed && <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)] px-1 mb-2">New Chat</p>}
        <div className={collapsed ? '' : 'grid grid-cols-2 gap-1.5'}>
          {Object.entries(MODES).map(([mode, meta]) => (
            <button key={mode} onClick={() => onNew(mode)} title={`New ${meta.label} chat`}
              className={`transition-all ${collapsed ? 'w-9 h-9 rounded-xl hover:bg-[var(--mint)] dark:hover:bg-[#1e3028] flex items-center justify-center text-base' : 'flex items-center gap-1.5 px-2.5 py-2 rounded-xl hover:bg-[var(--mint)] dark:hover:bg-[#1e3028] text-xs text-[var(--ink)] border border-[var(--border)] hover:border-[var(--sage)]'}`}>
              <span>{meta.emoji}</span>{!collapsed && <span className="truncate font-medium">{meta.label}</span>}
            </button>
          ))}
        </div>
      </div>

      {/* Chat history */}
      {!collapsed && (
        <div className="flex-1 overflow-y-auto py-2 px-2 space-y-0.5">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)] px-1 mb-1.5">Recent Chats</p>
          {sessions.length === 0 && <p className="text-xs text-[var(--muted)] px-2 py-3 text-center">Start a chat above</p>}
          {sessions.map(s => (
            <div key={s.id}
              className={`group flex items-center gap-2 px-2 py-2 rounded-xl cursor-pointer transition-all ${activeId === s.id ? 'sidebar-active' : 'hover:bg-[var(--mint)] dark:hover:bg-[#1e2e26]'}`}
              onClick={() => onSelect(s.id)}>
              <span className="text-sm flex-shrink-0">{MODES[s.mode]?.emoji || '💬'}</span>
              {editId === s.id ? (
                <input value={editTitle} onChange={e => setEditTitle(e.target.value)}
                  onBlur={() => saveEdit(s.id)} onKeyDown={e => e.key === 'Enter' && saveEdit(s.id)}
                  autoFocus onClick={e => e.stopPropagation()}
                  className="flex-1 text-xs bg-white dark:bg-[#2a3a30] rounded-lg px-2 py-0.5 text-[var(--ink)] outline-none min-w-0" />
              ) : (
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium truncate">{s.title}</p>
                  <p className={`text-[10px] ${activeId === s.id ? 'text-emerald-200' : 'text-[var(--muted)]'}`}>{timeAgo(s.updated_at)}</p>
                </div>
              )}
              <div className={`flex gap-0.5 flex-shrink-0 ${editId === s.id ? '' : 'opacity-0 group-hover:opacity-100'} transition-opacity`}>
                <button onClick={e => startEdit(s, e)} className={`p-1 rounded-lg ${activeId === s.id ? 'hover:bg-white/20' : 'hover:bg-[var(--border)]'}`}>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                </button>
                <button onClick={e => { e.stopPropagation(); onDelete(s.id) }} className={`p-1 rounded-lg ${activeId === s.id ? 'hover:bg-white/20 text-red-200' : 'hover:bg-[var(--border)] text-red-400'}`}>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" /></svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tools + theme */}
      <div className={`border-t border-[var(--border)] py-2 flex-shrink-0 overflow-y-auto ${collapsed ? 'flex flex-col items-center gap-0.5' : 'px-2'}`}>
        {!collapsed && <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)] px-1 mb-1.5">Services & Tools</p>}
        {TOOLS.map(t => (
          <button key={t.id} onClick={() => onSelect('tool:' + t.id)} title={t.label}
            className={`transition-all ${collapsed ? 'w-9 h-9 rounded-xl flex items-center justify-center text-base' : 'w-full flex items-center gap-2 px-2 py-2 rounded-xl text-xs'} ${activeId === 'tool:' + t.id ? 'sidebar-active' : 'hover:bg-[var(--mint)] dark:hover:bg-[#1e3028] text-[var(--ink)]'}`}>
            <span>{t.emoji}</span>{!collapsed && <span className="font-medium">{t.label}</span>}
          </button>
        ))}
        <button onClick={onToggleDark} title="Toggle theme"
          className={`transition-all mt-1 ${collapsed ? 'w-9 h-9 rounded-xl flex items-center justify-center' : 'w-full flex items-center gap-2 px-2 py-2 rounded-xl text-xs'} hover:bg-[var(--mint)] dark:hover:bg-[#1e3028] text-[var(--muted)]`}>
          <span>{dark ? '☀️' : '🌙'}</span>{!collapsed && <span>{dark ? 'Light Mode' : 'Dark Mode'}</span>}
        </button>
        {collapsed && (
          <button onClick={onToggle} className="w-9 h-9 rounded-xl hover:bg-[var(--mint)] dark:hover:bg-[#1e3028] flex items-center justify-center text-[var(--muted)] mt-1">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18l6-6-6-6" /></svg>
          </button>
        )}
      </div>
    </div>
  )
}

// ── APP ROOT ──────────────────────────────────────────────────────────────────
export default function App() {
  const [dark, toggleDark] = useTheme()
  const [sessions, setSessions] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [activeSession, setActiveSession] = useState(null)
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => { API.getSessions().then(setSessions).catch(() => {}) }, [])

  useEffect(() => {
    if (!activeId || activeId.startsWith('tool:')) { setActiveSession(null); return }
    API.getSession(activeId).then(setActiveSession).catch(() => {})
  }, [activeId])

  const handleNew = async mode => {
    const s = await API.createSession(mode, 'New Chat')
    setSessions(p => [s, ...p]); setActiveId(s.id); setMobileOpen(false)
  }
  const handleDelete = async id => {
    if (!confirm('Delete this chat?')) return
    await API.deleteSession(id)
    setSessions(p => p.filter(s => s.id !== id))
    if (activeId === id) setActiveId(null)
  }
  const handleRename = async (id, title) => {
    const u = await API.renameSession(id, title)
    setSessions(p => p.map(s => s.id === id ? { ...s, title: u.title } : s))
  }
  const handleUpdate = useCallback(() => {
    API.getSessions().then(setSessions)
    if (activeId && !activeId.startsWith('tool:')) API.getSession(activeId).then(setActiveSession)
  }, [activeId])

  const toolId = activeId?.startsWith('tool:') ? activeId.replace('tool:', '') : null
  const toolLabel = TOOLS.find(t => t.id === toolId)

  return (
    <div className="flex h-screen overflow-hidden" style={{ fontFamily: "'Instrument Sans', system-ui, sans-serif", background: 'var(--cream)' }}>
      {/* Mobile overlay */}
      {mobileOpen && <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-20 md:hidden" onClick={() => setMobileOpen(false)} />}

      {/* Sidebar */}
      <div className={`fixed md:relative z-30 h-full shadow-xl md:shadow-none transition-transform duration-300 ${mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}>
        <Sidebar sessions={sessions} activeId={activeId}
          onSelect={id => { setActiveId(id); setMobileOpen(false) }}
          onNew={handleNew} onDelete={handleDelete} onRename={handleRename}
          collapsed={collapsed} onToggle={() => setCollapsed(c => !c)}
          dark={dark} onToggleDark={toggleDark} />
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mobile top bar */}
        <div className="md:hidden flex items-center gap-3 px-4 py-3 bg-[var(--warm-white)] dark:bg-[#0f1a15] border-b border-[var(--border)] flex-shrink-0">
          <button onClick={() => setMobileOpen(true)} className="text-[var(--muted)] p-1">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12h18M3 6h18M3 18h18" /></svg>
          </button>
          <p className="font-display font-semibold text-[var(--ink)] text-sm truncate">
            {activeSession?.title || (toolLabel ? `${toolLabel.emoji} ${toolLabel.label}` : '✚ MediAgent')}
          </p>
        </div>

        <div className="flex-1 overflow-hidden">
          {/* Welcome screen */}
          {!activeId && (
            <div className="flex flex-col items-center justify-center h-full text-center px-6 gap-8 overflow-y-auto py-10 bg-[var(--cream)] dark:bg-[#0d1512]">
              <div className="anim-up">
                <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-[var(--forest-light)] to-[var(--forest)] flex items-center justify-center text-4xl shadow-2xl mx-auto mb-5">✚</div>
                <h1 className="font-display font-bold text-4xl gradient-text">MediAgent</h1>
                <p className="text-[var(--muted)] mt-2 text-sm max-w-sm mx-auto leading-relaxed">AI Medical Copilot — persistent chats, appointments, email & WhatsApp notifications, drug checking, and live web search.</p>
              </div>

              <div className="w-full max-w-lg space-y-4 anim-up delay-1">
                <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)] text-left">💬 Start a Chat</p>
                <div className="grid grid-cols-2 gap-3">
                  {Object.entries(MODES).map(([mode, meta]) => (
                    <button key={mode} onClick={() => handleNew(mode)}
                      className="p-4 rounded-2xl bg-[var(--warm-white)] dark:bg-[#1a2420] hover:bg-[var(--mint)] dark:hover:bg-[#1e3028] border border-[var(--border)] hover:border-[var(--sage)] text-left transition-all hover:shadow-md group">
                      <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${meta.grad} flex items-center justify-center text-xl mb-3 group-hover:scale-110 transition-transform shadow-sm`}>{meta.emoji}</div>
                      <p className="font-display font-bold text-sm text-[var(--ink)]">{meta.label}</p>
                      <p className="text-xs text-[var(--muted)] mt-0.5">{meta.hint}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div className="w-full max-w-lg space-y-4 anim-up delay-2">
                <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)] text-left">🛠 Agentic Services</p>
                <div className="grid grid-cols-3 gap-2.5">
                  {TOOLS.map(t => (
                    <button key={t.id} onClick={() => setActiveId('tool:' + t.id)}
                      className="p-3.5 rounded-xl bg-[var(--warm-white)] dark:bg-[#1a2420] hover:bg-[var(--mint)] dark:hover:bg-[#1e3028] border border-[var(--border)] hover:border-[var(--sage)] text-center transition-all hover:shadow-sm group">
                      <div className="text-2xl mb-1.5 group-hover:scale-110 transition-transform">{t.emoji}</div>
                      <p className="font-semibold text-xs text-[var(--ink)]">{t.label}</p>
                      <p className="text-[10px] text-[var(--muted)] mt-0.5 leading-tight">{t.desc}</p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Tool panels */}
          {toolId === 'appointments' && <div className="h-full overflow-y-auto bg-[var(--warm-white)] dark:bg-[#111815]"><AppointmentsPanel /></div>}
          {toolId === 'notify'       && <div className="h-full overflow-y-auto bg-[var(--warm-white)] dark:bg-[#111815]"><NotificationsPanel /></div>}
          {toolId === 'search'       && <div className="h-full overflow-y-auto bg-[var(--warm-white)] dark:bg-[#111815]"><SearchAgent /></div>}
          {toolId === 'drug'         && <div className="h-full overflow-y-auto bg-[var(--warm-white)] dark:bg-[#111815]"><DrugChecker /></div>}
          {toolId === 'medicine'     && <div className="h-full overflow-y-auto bg-[var(--warm-white)] dark:bg-[#111815]"><MedicineInfo /></div>}
          {toolId === 'medtracker'   && <div className="h-full overflow-y-auto bg-[var(--warm-white)] dark:bg-[#111815]"><MedTracker /></div>}
          {toolId === 'bmi'          && <div className="h-full overflow-y-auto bg-[var(--warm-white)] dark:bg-[#111815]"><BMICalc /></div>}

          {/* Chat */}
          {activeSession && <div className="h-full bg-[var(--cream)] dark:bg-[#0d1512]"><ChatWindow session={activeSession} onUpdate={handleUpdate} /></div>}
        </div>
      </div>
    </div>
  )
}
