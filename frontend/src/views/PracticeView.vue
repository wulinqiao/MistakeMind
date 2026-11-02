<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { diagnoseSentence, fetchQuestion, fetchQuestions, submitAnswer } from '../api'
import { PRACTICE_MODES, USER_ID, messageForError } from '../constants'
import { clearQuestionDraft, loadPracticeSession, savePracticeSession } from '../practiceSession'
import { notifyAttemptSaved } from '../refreshSignal'
import ErrorAlert from '../components/ErrorAlert.vue'
import HintPanel from '../components/HintPanel.vue'
import DiagnosisCard from '../components/DiagnosisCard.vue'

defineOptions({ name: 'PracticeView' })

const LOCK_MS = 10000
const COUNTDOWN_SEC = 5

const route = useRoute()
const router = useRouter()
const mode = ref('判断题')
const difficulty = ref('')
const category = ref('')

const question = ref(null)
const answer = ref('')
const hintLevel = ref(0)
const hints = ref([])
const hintsLoading = ref(false)
const hintsUnlocked = ref(false)
const hintCountdown = ref(null)
const hintUnlockAt = ref(null)
const diagnosis = ref(null)
const attemptNumber = ref(1)
const loading = ref(false)
const submitting = ref(false)
const result = ref(null)
const errorCode = ref('')
const errorMessage = ref('')
let loadVersion = 0
let lockTimer = null
let countdownTimer = null

const options = computed(() => {
  if (!question.value) return []
  if (question.value.options?.length) return question.value.options
  if (question.value.mode === '判断题') return ['是病句', '不是病句']
  return []
})

const canSubmit = computed(() => answer.value.trim().length > 0 && !submitting.value && !loading.value && !result.value)

const answerType = computed(() => {
  if (mode.value === '修改题') return 'text'
  return 'choice'
})

function clearHintTimers() {
  if (lockTimer) {
    clearTimeout(lockTimer)
    lockTimer = null
  }
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

function persistDraft() {
  if (!question.value) return
  sessionStorage.setItem('mm_last_question_id', question.value.question_id)
  savePracticeSession({
    mode: mode.value,
    difficulty: difficulty.value || '',
    category: category.value || '',
    questionDraft: {
      question_id: question.value.question_id,
      question: question.value,
      answer: answer.value,
      hintLevel: hintLevel.value,
      hints: hints.value,
      hintsUnlocked: hintsUnlocked.value,
      hintUnlockAt: hintUnlockAt.value,
      diagnosis: diagnosis.value,
      attemptNumber: attemptNumber.value,
      result: result.value,
      mode: mode.value,
      difficulty: difficulty.value,
      category: category.value,
    },
  })
}

function restoreDraft(questionId) {
  const draft = loadPracticeSession().questionDraft
  if (!draft || draft.question_id !== questionId || !draft.question) return false
  question.value = draft.question
  answer.value = draft.answer || ''
  hintLevel.value = draft.hintLevel || 0
  hints.value = Array.isArray(draft.hints) ? draft.hints : []
  hintsUnlocked.value = Boolean(draft.hintsUnlocked)
  hintUnlockAt.value = draft.hintUnlockAt || null
  diagnosis.value = draft.diagnosis || null
  attemptNumber.value = draft.attemptNumber || 1
  result.value = draft.result || null
  if (draft.mode) mode.value = draft.mode
  difficulty.value = draft.difficulty || difficulty.value
  category.value = draft.category || category.value
  resumeHintUnlock()
  if (!hints.value.length && !result.value) ensureHints(question.value)
  return true
}

function resumeHintUnlock() {
  clearHintTimers()
  if (hintsUnlocked.value || result.value) {
    hintCountdown.value = null
    return
  }
  const unlockAt = Number(hintUnlockAt.value || 0)
  if (!unlockAt) {
    startHintUnlock()
    return
  }
  const remaining = unlockAt - Date.now()
  if (remaining <= 0) {
    hintsUnlocked.value = true
    hintCountdown.value = null
    persistDraft()
    return
  }
  if (remaining <= COUNTDOWN_SEC * 1000) {
    let left = Math.max(1, Math.ceil(remaining / 1000))
    hintCountdown.value = left
    countdownTimer = setInterval(() => {
      left -= 1
      if (left <= 0) {
        clearInterval(countdownTimer)
        countdownTimer = null
        hintCountdown.value = null
        hintsUnlocked.value = true
        persistDraft()
      } else {
        hintCountdown.value = left
      }
    }, 1000)
    return
  }
  lockTimer = setTimeout(() => {
    let left = COUNTDOWN_SEC
    hintCountdown.value = left
    countdownTimer = setInterval(() => {
      left -= 1
      if (left <= 0) {
        clearInterval(countdownTimer)
        countdownTimer = null
        hintCountdown.value = null
        hintsUnlocked.value = true
        persistDraft()
      } else {
        hintCountdown.value = left
      }
    }, 1000)
  }, remaining - COUNTDOWN_SEC * 1000)
}

function startHintUnlock() {
  clearHintTimers()
  hintsUnlocked.value = false
  hintCountdown.value = null
  hintUnlockAt.value = Date.now() + LOCK_MS + COUNTDOWN_SEC * 1000
  lockTimer = setTimeout(() => {
    let left = COUNTDOWN_SEC
    hintCountdown.value = left
    countdownTimer = setInterval(() => {
      left -= 1
      if (left <= 0) {
        clearInterval(countdownTimer)
        countdownTimer = null
        hintCountdown.value = null
        hintsUnlocked.value = true
        persistDraft()
      } else {
        hintCountdown.value = left
      }
    }, 1000)
  }, LOCK_MS)
}

function applyRouteQuery() {
  const q = route.query
  if (typeof q.mode === 'string' && PRACTICE_MODES.includes(q.mode)) {
    mode.value = q.mode
  }
  difficulty.value = typeof q.difficulty === 'string' ? q.difficulty : ''
  category.value = typeof q.category === 'string' ? q.category : ''
}

async function ensureHints(current) {
  if (!current || hintsLoading.value) return
  hintsLoading.value = true
  try {
    const data = await diagnoseSentence({
      sentence: current.sentence,
      user_id: USER_ID,
      need_hints: true,
    })
    if (question.value?.question_id !== current.question_id) return
    hints.value = data.review_status === 'passed' && !data.needs_context ? data.hints || [] : []
    persistDraft()
  } catch {
    if (question.value?.question_id === current.question_id) hints.value = []
  } finally {
    hintsLoading.value = false
  }
}

async function loadQuestion(questionId = null, { force = false } = {}) {
  if (!force && questionId && restoreDraft(questionId)) {
    loading.value = false
    return
  }

  const version = ++loadVersion
  clearHintTimers()
  errorCode.value = ''
  errorMessage.value = ''
  result.value = null
  answer.value = ''
  hintLevel.value = 0
  hints.value = []
  hintsUnlocked.value = false
  hintCountdown.value = null
  hintUnlockAt.value = null
  diagnosis.value = null
  attemptNumber.value = 1
  question.value = null
  loading.value = true

  try {
    const data = questionId
      ? await fetchQuestion(questionId)
      : await fetchQuestions({
          mode: mode.value,
          difficulty: difficulty.value || undefined,
          category: category.value || undefined,
          count: 1,
          user_id: USER_ID,
        })
    if (version !== loadVersion) return
    question.value = data.question || data.questions?.[0] || null
    if (!question.value) {
      errorCode.value = 'QUESTION_NOT_FOUND'
      errorMessage.value = '暂无符合条件的题目'
      clearQuestionDraft()
    } else {
      if (question.value.mode) mode.value = question.value.mode
      startHintUnlock()
      ensureHints(question.value)
      persistDraft()
    }
  } catch (err) {
    if (version !== loadVersion) return
    errorCode.value = err.code || 'INTERNAL_ERROR'
    errorMessage.value = messageForError(err)
  } finally {
    if (version === loadVersion) loading.value = false
  }
}

function loadNextQuestion() {
  clearQuestionDraft()
  const id = result.value?.recommended_question_id
  if (id) {
    if (route.query.question_id === id) loadQuestion(id, { force: true })
    else {
      router.replace({
        path: '/practice/question',
        query: {
          mode: mode.value,
          difficulty: difficulty.value || undefined,
          category: category.value || undefined,
          question_id: id,
        },
      })
    }
  } else if (route.query.question_id) {
    router.replace({
      path: '/practice/question',
      query: {
        mode: mode.value,
        difficulty: difficulty.value || undefined,
        category: category.value || undefined,
      },
    })
  } else {
    loadQuestion(null, { force: true })
  }
}

async function submit() {
  if (!canSubmit.value || !question.value) return
  errorCode.value = ''
  errorMessage.value = ''
  submitting.value = true
  try {
    result.value = await submitAnswer({
      user_id: USER_ID,
      question_id: question.value.question_id,
      answer: answer.value.trim(),
      answer_type: answerType.value,
      hint_level_used: hintLevel.value,
      attempt_number: attemptNumber.value,
    })
    diagnosis.value = result.value.diagnosis || null
    persistDraft()
    notifyAttemptSaved()
  } catch (err) {
    errorCode.value = err.code || 'INTERNAL_ERROR'
    errorMessage.value = messageForError(err)
  } finally {
    submitting.value = false
  }
}

watch(
  () => [route.query.mode, route.query.difficulty, route.query.category, route.query.question_id],
  () => {
    applyRouteQuery()
    const qid = typeof route.query.question_id === 'string' ? route.query.question_id : null
    if (qid && question.value?.question_id === qid) {
      persistDraft()
      return
    }
    loadQuestion(qid)
  },
  { immediate: true },
)

watch([answer, hintLevel], () => {
  if (question.value) persistDraft()
})

onBeforeUnmount(clearHintTimers)
</script>

<template>
  <div class="neu-stack">
    <header class="question-header">
      <div class="question-header-text">
        <h1 class="neu-section-title">答题</h1>
        <p class="neu-copy">三种题型共用本页。可先看分层提示再作答；提交后查看反馈与讲解。</p>
      </div>
      <div class="question-header-actions">
        <button class="neu-btn neu-btn-primary" type="button" :disabled="!canSubmit" @click="submit">
          {{ submitting ? '提交中…' : '提交' }}
        </button>
        <button
          class="neu-btn"
          type="button"
          :disabled="loading || submitting"
          @click="loadNextQuestion"
        >
          下一题
        </button>
      </div>
    </header>

    <ErrorAlert v-if="errorMessage" :code="errorCode" :message="errorMessage" />
    <p v-if="loading" class="neu-copy">正在加载题目…</p>

    <template v-else-if="question">
      <p class="neu-well neu-copy">{{ question.sentence }}</p>
      <p class="neu-kicker">{{ question.difficulty }} · {{ question.mode }} · 第 {{ attemptNumber }} 次作答</p>

      <div v-if="mode === '判断题' || mode === '选择题'" class="neu-choice-row">
        <button
          v-for="option in options"
          :key="option"
          type="button"
          class="neu-chip"
          :class="{ 'is-active': answer === option }"
          :disabled="!!result"
          @click="answer = option"
        >
          {{ option }}
        </button>
      </div>

      <label v-else class="neu-field">
        <span class="neu-label">你的修改</span>
        <textarea
          v-model="answer"
          class="neu-textarea"
          placeholder="尽量少改，保持原意"
          :disabled="!!result"
        />
      </label>

      <HintPanel
        v-model:level="hintLevel"
        :hints="hints"
        :unlocked="hintsUnlocked && hints.length > 0"
        :countdown="hintCountdown"
      />
      <p v-if="hintsUnlocked && !hints.length && !hintsLoading" class="neu-kicker">
        暂无分层提示，可直接作答。
      </p>

      <section v-if="result" class="neu-stack" style="gap: 16px">
        <article class="neu-card">
          <h3 :class="result.is_correct ? 'neu-ok' : 'neu-bad'">
            {{ result.is_correct ? '回答正确' : '再想一想' }}
          </h3>
          <p class="neu-result-block">{{ result.feedback }}</p>
          <p v-if="result.feedback_level" class="neu-kicker">反馈级别：{{ result.feedback_level }}</p>
        </article>
        <DiagnosisCard v-if="diagnosis" :diagnosis="diagnosis" />
      </section>
    </template>
  </div>
</template>
