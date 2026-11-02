import { apiRequest } from './client'

export function fetchStatus() {
  return apiRequest('/api/status')
}

export function diagnoseSentence(payload) {
  return apiRequest('/api/diagnose', { method: 'POST', body: payload })
}

export function fetchQuestions(params = {}) {
  return apiRequest('/api/questions', { query: params })
}

export function fetchQuestion(questionId) {
  return apiRequest(`/api/questions/${encodeURIComponent(questionId)}`)
}

export function submitAnswer(payload) {
  return apiRequest('/api/submit-answer', { method: 'POST', body: payload })
}

export function fetchHistory(userId, params = {}) {
  return apiRequest(`/api/history/${encodeURIComponent(userId)}`, { query: params })
}

export function fetchProfile(userId) {
  return apiRequest(`/api/profile/${encodeURIComponent(userId)}`)
}
