import axios from 'axios'

const API_BASE = ''

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.reload()
    }
    return Promise.reject(error)
  }
)

export default api

export async function login(username: string, password: string) {
  const res = await api.post('/api/login', { username, password })
  return res.data
}

export async function getMe() {
  const res = await api.get('/api/me')
  return res.data
}

export async function getChannels(page = 1, limit = 20) {
  const res = await api.get(`/api/channels?page=${page}&limit=${limit}`)
  return res.data
}

export async function createChannel(data: any) {
  const res = await api.post('/api/channels', data)
  return res.data
}

export async function updateChannel(id: number, data: any) {
  const res = await api.put(`/api/channels/${id}`, data)
  return res.data
}

export async function deleteChannel(id: number) {
  const res = await api.delete(`/api/channels/${id}`)
  return res.data
}

export async function batchUpdateChannels(ids: number[], status: number) {
  const res = await api.post('/api/channels/batch-update', { ids, status })
  return res.data
}

export async function batchDeleteChannels(ids: number[]) {
  const res = await api.post('/api/channels/batch-delete', { ids })
  return res.data
}

export async function testChannel(id: number) {
  const res = await api.post(`/api/channels/${id}/test`)
  return res.data
}

export async function getChannelHealth(id: number) {
  const res = await api.get(`/api/channels/${id}/health`)
  return res.data
}

export async function resetChannelHealth(id: number) {
  const res = await api.post(`/api/channels/${id}/reset-health`)
  return res.data
}

export async function getTokens(page = 1, limit = 20) {
  const res = await api.get(`/api/tokens?page=${page}&limit=${limit}`)
  return res.data
}

export async function createToken(data: any) {
  const res = await api.post('/api/tokens', data)
  return res.data
}

export async function deleteToken(id: number) {
  const res = await api.delete(`/api/tokens/${id}`)
  return res.data
}

export async function batchUpdateTokens(ids: number[], status: number) {
  const res = await api.post('/api/tokens/batch-update', { ids, status })
  return res.data
}

export async function batchDeleteTokens(ids: number[]) {
  const res = await api.post('/api/tokens/batch-delete', { ids })
  return res.data
}

export async function getPools(page = 1, limit = 20) {
  const res = await api.get(`/api/model-pools?page=${page}&limit=${limit}`)
  return res.data
}

export async function createPool(data: any) {
  const res = await api.post('/api/model-pools', data)
  return res.data
}

export async function updatePool(id: number, data: any) {
  const res = await api.put(`/api/model-pools/${id}`, data)
  return res.data
}

export async function deletePool(id: number) {
  const res = await api.delete(`/api/model-pools/${id}`)
  return res.data
}

export async function getPoolMembers(poolId: number) {
  const res = await api.get(`/api/model-pools/${poolId}/members`)
  return res.data
}

export async function createPoolMember(poolId: number, data: any) {
  const res = await api.post(`/api/model-pools/${poolId}/members`, data)
  return res.data
}

export async function updatePoolMember(poolId: number, memberId: number, data: any) {
  const res = await api.put(`/api/model-pools/${poolId}/members/${memberId}`, data)
  return res.data
}

export async function deletePoolMember(poolId: number, memberId: number) {
  const res = await api.delete(`/api/model-pools/${poolId}/members/${memberId}`)
  return res.data
}

export async function getLogs(page = 1, limit = 20, tokenId?: number, model?: string) {
  let url = `/api/logs?page=${page}&limit=${limit}`
  if (tokenId) url += `&token_id=${tokenId}`
  if (model) url += `&model=${encodeURIComponent(model)}`
  const res = await api.get(url)
  return res.data
}

export async function getLogDetail(id: number) {
  const res = await api.get(`/api/logs/${id}`)
  return res.data
}

export async function replayLog(id: number) {
  const res = await api.post(`/api/logs/${id}/replay`)
  return res.data
}

export async function getDashboardStats() {
  const res = await api.get('/api/dashboard/stats')
  return res.data
}

export async function exportConfig() {
  const res = await api.get('/api/config/export')
  return res.data
}

export async function importConfig(data: any) {
  const res = await api.post('/api/config/import', data)
  return res.data
}

export async function reloadConfig() {
  const res = await api.post('/api/config/reload')
  return res.data
}

export async function syncChannelModels(channelId: number) {
  const res = await api.post(`/api/channels/${channelId}/sync-models`)
  return res.data
}

export async function getPlatforms() {
  const res = await api.get('/api/platforms')
  return res.data
}
