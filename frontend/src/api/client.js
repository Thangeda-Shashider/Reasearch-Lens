import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120_000,
})

// Papers
export const uploadPapers = (formData, onProgress) =>
  api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress,
  })

export const fetchPapers = () => api.get('/papers').then(r => r.data)

export const deletePaper = id => api.delete(`/papers/${id}`).then(r => r.data)

// Analysis
export const startAnalysis = (body = {}) =>
  api.post('/analyze', body).then(r => r.data)

export const fetchStatus = jobId =>
  api.get(`/status/${jobId}`).then(r => r.data)

// Gaps
export const fetchGaps = (params = {}) =>
  api.get('/gaps', { params }).then(r => r.data)

export const fetchGap = id => api.get(`/gaps/${id}`).then(r => r.data)

// Visualisations
export const fetchUmap = () =>
  api.get('/visualizations/umap').then(r => r.data)

export const fetchGraph = () =>
  api.get('/visualizations/graph').then(r => r.data)

// Report
export const exportReport = body =>
  api.post('/report/export', body, { responseType: 'blob' })

export default api
