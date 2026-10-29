import { messageForError } from '../constants'

const BASE_URL = import.meta.env.VITE_API_BASE || ''

export class ApiError extends Error {
  constructor(error, requestId = null) {
    super(messageForError(error))
    this.name = 'ApiError'
    this.code = error?.code || 'INTERNAL_ERROR'
    this.details = error?.details ?? null
    this.requestId = requestId
  }
}

export async function apiRequest(path, options = {}) {
  const { method = 'GET', query, body, headers = {} } = options
  const url = new URL(`${BASE_URL}${path}`, window.location.origin)

  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.set(key, String(value))
      }
    })
  }

  let response
  try {
    response = await fetch(url.toString(), {
      method,
      headers: {
        Accept: 'application/json',
        'X-Request-ID': `fe_${Date.now().toString(36)}`,
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError({ code: 'NETWORK_ERROR', message: messageForError({ code: 'NETWORK_ERROR' }) })
  }

  let payload
  try {
    payload = await response.json()
  } catch {
    throw new ApiError({ code: 'INTERNAL_ERROR', message: '响应不是合法 JSON' })
  }

  if (!payload?.success) {
    throw new ApiError(payload?.error || { code: 'INTERNAL_ERROR' }, payload?.request_id)
  }

  return payload.data
}
