<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { diagnoseSentence, fetchQuestion, fetchQuestions, submitAnswer } from '../api'
import { PRACTICE_MODES, USER_ID, messageForError } from '../constants'
import ErrorAlert from '../components/ErrorAlert.vue'
import HintPanel from '../components/HintPanel.vue'
import DiagnosisCard from '../components/DiagnosisCard.vue'

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
const diagnosis = ref(null)
const attemptNumber = ref(1)
const loading = ref(false)
const submitting = ref(false)
const result = ref(null)
const errorCode = ref('')
const errorMessage = ref('')
let loadVersion = 0

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

function applyRouteQuery() {
  const q = route.query
  if (typeof q.mode === 'string' && PRACTICE_MODES.includes(q.mode)) {
    mode.value = q.mode
  }
  difficulty.value = typeof q.difficulty === 'string' ? q.difficulty : ''
  category.value = typeof q.category === 'string' ? q.category : ''
}

async function loadQuestion(questionId = null) {
  const version = ++loadVersion
  errorCode.value = ''
  errorMessage.value = ''
  result.value = null
  answer.value = ''
  hintLevel.value = 0
  hints.value = []
  diagnosis.value = null
  attemptNumber.value = 1
  question.value = null
  loading.value = true

  try {
    const data = questionId ? await fetchQuestion(questionId) : await fetchQuestions({
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
    } else if (question.value.mode) {
      mode.value = question.value.mode
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
  const id = result.value?.recommended_question_id
  if (id) {
    if (route.query.question_id === id) loadQuestion(id)
    else router.replace({ path: '/practice', query: { mode: mode.value, question_id: id } })
  } else if (route.query.question_id) {
    router.replace({ path: '/practice', query: { mode: mode.value,
      difficulty: difficulty.value || undefined, category: category.value || undefined } })
  } else {
    loadQuestion()
  }
}

async function ensureHints() {
  if (!question.value || hints.value.length || hintsLoading.value) return
  const id = question.value.question_id
  hintsLoading.value = true
  errorCode.value = ''
  errorMessage.value = ''
  try {
    const data = await diagnoseSentence({
      sentence: question.value.sentence,
      user_id: USER_ID,
      need_hints: true,
    })
    if (question.value?.question_id !== id) return
    hints.value = data.review_status === 'passed' && !data.needs_context ? data.hints || [] : []
    if (!hints.value.length) {
      errorCode.value = 'MODEL_LOW_CONFIDENCE'
      errorMessage.value = '暂无分层提示，可直接作答或换一题。'
    }
  } catch (err) {
    errorCode.value = err.code || 'INTERNAL_ERROR'
    errorMessage.value = messageForError(err)
  } finally {
    hintsLoading.value = false
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
  } catch (err) {
    errorCode.value = err.code || 'INTERNAL_ERROR'
    errorMessage.value = messageForError(err)
  } finally {
    submitting.value = false
  }
}

function selectMode(next) {
  if (next === mode.value && !route.query.question_id) return
  router.replace({ path: '/practice', query: { ...route.query, mode: next, question_id: undefined } })
}

function retryAnswer() {
  attemptNumber.value += 1
  result.value = null
  diagnosis.value = null
  answer.value = ''
}

watch(
  () => [route.query.mode, route.query.difficulty, route.query.category, route.query.question_id],
  () => {
    applyRouteQuery()
    loadQuestion(typeof route.query.question_id === 'string' ? route.query.question_id : null)
  },
  { immediate: true },
)
</script>

<template>
  <div class="neu-stack">
    <header class="neu-stack">
      <h1 class="neu-section-title">答题</h1>
      <p class="neu-copy">三种题型共用本页。可先看分层提示再作答；提交后查看反馈与讲解。</p>
    </header>

    <div class="neu-choice-row" role="tablist" aria-label="练习模式">
      <button
        v-for="item in PRACTICE_MODES"
        :key="item"
        type="button"
        class="neu-chip"
        :disabled="submitting || hintsLoading"
        :class="{ 'is-active': mode === item }"
        @click="selectMode(item)"
      >
        {{ item }}
      </button>
    </div>

    <ErrorAlert v-if="errorMessage" :code="errorCode" :message="errorMessage" />

    <p v-if="loading" class="neu-copy">正在加载题目…</p>

    <template v-else-if="question">
      <p class="neu-well neu-copy">{{ question.sentence }}</p>
      <p class="neu-kicker">
        {{ question.difficulty }} · {{ question.mode }}
        · 第 {{ attemptNumber }} 次作答
      </p>

      <div class="neu-actions">
        <button
          class="neu-btn"
          type="button"
          :disabled="hintsLoading || !!hints.length"
          @click="ensureHints"
        >
          {{ hintsLoading ? '加载提示…' : hints.length ? '提示已就绪' : '加载分层提示' }}
        </button>
      </div>

      <HintPanel v-if="hints.length" v-model:level="hintLevel" :hints="hints" />

      <div v-if="mode === '判断题' || mode === '选择题'" class="neu-choice-row">
        <button
          v-for="option in options"
          :key="option"
          type="button"
          class="neu-chip"
          :class="{ 'is-active': answer === option }"
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
        />
      </label>

      <div class="neu-actions">
        <button class="neu-btn neu-btn-primary" type="button" :disabled="!canSubmit" @click="submit">
          {{ submitting ? '提交中…' : '提交答案' }}
        </button>
        <button class="neu-btn" type="button" :disabled="loading || submitting || hintsLoading" @click="loadNextQuestion">{{ result?.recommended_question_id ? '练习推荐题' : '下一题' }}</button>
      </div>

      <section v-if="result" class="neu-card">
        <h3 :class="result.is_correct ? 'neu-ok' : 'neu-bad'">
          {{ result.is_correct ? '回答正确' : '再想一想' }}
        </h3>
        <p class="neu-result-block">{{ result.feedback }}</p>
        <p v-if="result.feedback_level" class="neu-kicker">反馈级别：{{ result.feedback_level }}</p>
        <p v-if="result.mastery_update" class="neu-result-block">
          分类正确率：{{ result.mastery_update.category }}
          {{ Number(result.mastery_update.before).toFixed(2) }}
          → {{ Number(result.mastery_update.after).toFixed(2) }}
        </p>
        <p v-if="result.recommended_question_id" class="neu-kicker">
          已为你选择一道针对性练习，点击「练习推荐题」继续。
        </p>
        <button v-if="!result.is_correct" class="neu-btn" type="button" @click="retryAnswer">再答一次</button>
      </section>

    <DiagnosisCard v-if="diagnosis" :diagnosis="diagnosis" />
    <details v-if="result?.trace?.length" class="neu-card">
      <summary>查看本次执行过程</summary>
      <ol><li v-for="(step, index) in result.trace" :key="index">{{ step.agent }} · {{ step.action }} · {{ step.status }} · {{ step.duration_ms }} ms</li></ol>
    </details>
    </template>
  </div>
</template>
