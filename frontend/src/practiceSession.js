const KEY = 'mm_practice_session'

export function loadPracticeSession() {
  try {
    return JSON.parse(sessionStorage.getItem(KEY) || '{}') || {}
  } catch {
    return {}
  }
}

export function savePracticeSession(patch) {
  const next = { ...loadPracticeSession(), ...patch }
  sessionStorage.setItem(KEY, JSON.stringify(next))
  return next
}

export function clearQuestionDraft() {
  const session = loadPracticeSession()
  delete session.questionDraft
  sessionStorage.setItem(KEY, JSON.stringify(session))
}
