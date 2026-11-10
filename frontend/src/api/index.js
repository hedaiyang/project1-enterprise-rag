import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({ baseURL: '', timeout: 60000 })

// 请求拦截器：自动带 JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截器：401 跳登录
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('role')
      ElMessage.warning('登录已过期，请重新登录')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// 0. 登录（FormData）
export const login = (username, password) =>
  api.post('/api/login', new URLSearchParams({ username, password }))

// 1. 健康检查
export const getHealth = () => api.get('/api/health')

// 2. 列出所有源文档
export const getSources = () => api.get('/api/sources')

// 2.1 删除指定源文档（URL 编码文件名）
export const deleteSource = (source) => api.delete(`/api/sources/${encodeURIComponent(source)}`)

// 3. 上传文档入库
export const uploadFile = (file, device, securityLevel = 'V1') => {
  const fd = new FormData()
  fd.append('file', file)
  if (device) fd.append('device', device)
  fd.append('security_level', securityLevel)
  return api.post('/api/ingest', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
}

// 4. 同步问答
export const query = (queryText, device) =>
  api.post('/api/query', { query: queryText, device })

// 5. SSE 流式问答 —— 手动 fetch（axios 不支持 SSE）
// 流式末尾后端会下发 __SOURCES__<json>，直接解析来源，无需二次请求
export function queryStream(queryText, device, { onChunk, onSources, onDone, onError } = {}) {
  const token = localStorage.getItem('token')
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  fetch('/api/query/stream', {
    method: 'POST',
    headers,
    body: JSON.stringify({ query: queryText, device }),
  }).then(async (res) => {
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6)
        if (data === '[DONE]') { onDone && onDone(); return }
        if (data.startsWith('__SOURCES__')) {
          try { onSources && onSources(JSON.parse(data.slice(11))) } catch {}
          continue
        }
        onChunk && onChunk(data)
      }
    }
    onDone && onDone()
  }).catch(onError)
}
