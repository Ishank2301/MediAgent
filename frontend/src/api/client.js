import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// Global error interceptor - normalise all errors
api.interceptors.response.use(
  r => r,
  err => {
    const detail = err.response?.data?.detail
    if (detail) err.message = typeof detail === 'string' ? detail : JSON.stringify(detail)
    return Promise.reject(err)
  }
)

// ── Sessions / Chat ────────────────────────────────────────────────────────
export const getSessions    = ()            => api.get('/sessions').then(r=>r.data)
export const createSession  = (mode,title)  => api.post('/sessions',{mode,title}).then(r=>r.data)
export const getSession     = id            => api.get(`/sessions/${id}`).then(r=>r.data)
export const renameSession  = (id,title)    => api.patch(`/sessions/${id}`,{title}).then(r=>r.data)
export const deleteSession  = id            => api.delete(`/sessions/${id}`).then(r=>r.data)
export const sendMessage    = (sid,msg,mode)=> api.post(`/sessions/${sid}/chat`,{message:msg,mode}).then(r=>r.data)

// File upload (image or PDF) — returns same shape as sendMessage
export const sendFile = (sid, file, message='', mode='general') => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('message', message)
  fd.append('mode', mode)
  return api.post(`/sessions/${sid}/chat/upload`, fd, {
    headers: {'Content-Type': 'multipart/form-data'},
    timeout: 90000,  // longer for vision processing
  }).then(r=>r.data)
}

// ── Tools ──────────────────────────────────────────────────────────────────
export const checkInteraction = drugs  => api.post('/interaction',{drugs}).then(r=>r.data)
export const getMedicineInfo  = name   => api.get(`/medicine/${encodeURIComponent(name)}`).then(r=>r.data)

// ── Adherence ──────────────────────────────────────────────────────────────
export const getMedications   = uid         => api.get('/medications',{params:{user_id:uid}}).then(r=>r.data)
export const addMedication    = data        => api.post('/medications',data).then(r=>r.data)
export const deleteMedication = id          => api.delete(`/medications/${id}`).then(r=>r.data)
export const logDose          = (mid,data)  => api.post(`/medications/${mid}/log`,data).then(r=>r.data)
export const getSchedule      = uid         => api.get('/schedule',{params:{user_id:uid}}).then(r=>r.data)
export const getAdherence     = (uid,days)  => api.get('/adherence',{params:{user_id:uid,days}}).then(r=>r.data)

// ── Export ─────────────────────────────────────────────────────────────────
export const exportSession   = id  => api.get(`/export/session/${id}`,{responseType:'blob'}).then(r=>r.data)
export const exportAdherence = uid => api.get('/export/adherence',{params:{user_id:uid},responseType:'blob'}).then(r=>r.data)

// ── Appointments ───────────────────────────────────────────────────────────
export const getAppointments = uid          => api.get('/appointments',{params:{user_id:uid}}).then(r=>r.data)
export const bookAppointment = data         => api.post('/appointments',data).then(r=>r.data)
export const cancelAppt      = id           => api.delete(`/appointments/${id}`).then(r=>r.data)
export const sendReminder    = (id,channels)=> api.post(`/appointments/${id}/remind`,{channels}).then(r=>r.data)

// ── Notifications ──────────────────────────────────────────────────────────
export const testNotif       = data => api.post('/notify/test',data).then(r=>r.data)
export const sendMedReminder = data => api.post('/notify/medications',data).then(r=>r.data)
export const sendAdherenceRpt= data => api.post('/notify/adherence-report',data).then(r=>r.data)

// ── Search agent ───────────────────────────────────────────────────────────
export const searchDrug      = name     => api.get(`/search/drug/${encodeURIComponent(name)}`).then(r=>r.data)
export const searchNews      = topic    => api.get('/search/news',{params:{topic}}).then(r=>r.data)
export const findSpecialists = symptoms => api.get('/search/specialists',{params:{symptoms}}).then(r=>r.data)

// ── System ─────────────────────────────────────────────────────────────────
export const getHealth       = () => api.get('/').then(r=>r.data)
