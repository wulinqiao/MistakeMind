<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchQuestions } from '../api'
import { CATEGORIES, DIFFICULTIES, PRACTICE_MODES, messageForError } from '../constants'
import { loadPracticeSession, savePracticeSession } from '../practiceSession'
import ErrorAlert from '../components/ErrorAlert.vue'

defineOptions({ name: 'BankView' })

const PAGE_SIZE = 5
const FETCH_SIZE = 10

const route = useRoute()
const router = useRouter()
const saved = loadPracticeSession()

const mode = ref(saved.mode || '判断题')
const difficulty = ref(DIFFICULTIES.includes(saved.difficulty) ? saved.difficulty : '初中')
const category = ref(saved.category || '')
const page = ref(saved.page || 1)
const pool = ref(Array.isArray(saved.pool) ? saved.pool : [])
const loading = ref(false)
const loadingMore = ref(false)
const exhausted = ref(Boolean(saved.exhausted))
const errorCode = ref('')
const errorMessage = ref('')
let loadVersion = 0
// Only reuse cached list when it actually has questions; empty cache must refetch.
let skipNextReload = Boolean(saved.pool?.length)

const totalPages = computed(() => Math.max(1, Math.ceil(pool.value.length / PAGE_SIZE) || 1))
const pageItems = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE
  return pool.value.slice(start, start + PAGE_SIZE)
})
const canPrev = computed(() => page.value > 1)
const canNext = computed(() => page.value < totalPages.value || (!exhausted.value && pool.value.length > 0))

function persistBank() {
  sessionStorage.setItem('mm_bank_mode', mode.value)
  if (difficulty.value) sessionStorage.setItem('mm_bank_difficulty', difficulty.value)
  else sessionStorage.removeItem('mm_bank_difficulty')
  if (category.value) sessionStorage.setItem('mm_bank_category', category.value)
  else sessionStorage.removeItem('mm_bank_category')

  savePracticeSession({
    mode: mode.value,
    difficulty: difficulty.value || '',
    category: category.value || '',
    page: page.value,
    pool: pool.value,
    exhausted: exhausted.value,
  })
}

function applyRouteQuery() {
  const q = route.query
  if (typeof q.mode === 'string' && PRACTICE_MODES.includes(q.mode)) mode.value = q.mode
  if (typeof q.difficulty === 'string' && DIFFICULTIES.includes(q.difficulty)) difficulty.value = q.difficulty
  else if (q.difficulty === undefined && !skipNextReload && !saved.difficulty) difficulty.value = difficulty.value
  if (typeof q.category === 'string' && CATEGORIES.includes(q.category)) category.value = q.category
  else if (q.category === undefined || q.category === '') {
    if (typeof q.category === 'string') category.value = ''
  }
}

function filterKey(modeValue, difficultyValue, categoryValue) {
  return `${modeValue || ''}|${difficultyValue || ''}|${categoryValue || ''}`
}

async function fetchBatch(excludeIds = new Set()) {
  const data = await fetchQuestions({
    mode: mode.value,
    difficulty: difficulty.value || undefined,
    category: category.value || undefined,
    count: FETCH_SIZE,
  })
  const list = data.questions || []
  return list.filter((item) => item?.question_id && !excludeIds.has(item.question_id))
}

async function reload() {
  const version = ++loadVersion
  loading.value = true
  errorCode.value = ''
  errorMessage.value = ''
  page.value = 1
  exhausted.value = false
  try {
    const list = await fetchBatch()
    if (version !== loadVersion) return
    pool.value = list
    exhausted.value = list.length < FETCH_SIZE
    if (!list.length) {
      errorCode.value = 'QUESTION_NOT_FOUND'
      errorMessage.value = '暂无符合条件的题目'
    }
    persistBank()
  } catch (err) {
    if (version !== loadVersion) return
    pool.value = []
    exhausted.value = true
    errorCode.value = err.code || 'INTERNAL_ERROR'
    errorMessage.value = messageForError(err)
    persistBank()
  } finally {
    if (version === loadVersion) loading.value = false
  }
}

async function goNext() {
  if (page.value < totalPages.value) {
    page.value += 1
    persistBank()
    return
  }
  if (loadingMore.value) return
  loadingMore.value = true
  errorCode.value = ''
  errorMessage.value = ''
  try {
    const known = new Set(pool.value.map((item) => item.question_id))
    const extra = await fetchBatch(known)
    if (extra.length) {
      pool.value = [...pool.value, ...extra]
      page.value += 1
      if (extra.length < FETCH_SIZE) exhausted.value = true
    } else {
      exhausted.value = true
    }
    persistBank()
  } catch (err) {
    errorCode.value = err.code || 'INTERNAL_ERROR'
    errorMessage.value = messageForError(err)
  } finally {
    loadingMore.value = false
  }
}

function openQuestion(item) {
  sessionStorage.setItem('mm_last_question_id', item.question_id)
  persistBank()
  router.push({
    path: '/practice/question',
    query: {
      question_id: item.question_id,
      mode: item.mode || mode.value,
      difficulty: difficulty.value || undefined,
      category: category.value || undefined,
    },
  })
}

function syncFiltersToRoute() {
  router.replace({
    path: '/practice',
    query: {
      mode: mode.value,
      difficulty: difficulty.value || undefined,
      category: category.value || undefined,
    },
  })
}

watch(
  () => [route.query.mode, route.query.difficulty, route.query.category],
  () => {
    const before = filterKey(mode.value, difficulty.value, category.value)
    applyRouteQuery()
    const after = filterKey(mode.value, difficulty.value, category.value)
    if (skipNextReload && pool.value.length && before === after) {
      skipNextReload = false
      persistBank()
      return
    }
    skipNextReload = false
    reload()
  },
  { immediate: true },
)

watch([mode, difficulty, category], () => {
  const next = {
    mode: mode.value,
    difficulty: difficulty.value || undefined,
    category: category.value || undefined,
  }
  const same =
    route.query.mode === next.mode &&
    (route.query.difficulty || undefined) === next.difficulty &&
    (route.query.category || undefined) === next.category
  if (!same) syncFiltersToRoute()
  else persistBank()
})

watch(page, () => persistBank())
</script>

<template>
  <div class="neu-stack">
    <header class="neu-stack" style="gap: 8px">
      <h1 class="neu-section-title">题库</h1>
    </header>

    <section class="neu-stack">
      <h2 class="neu-section-title">选择练习条件</h2>

      <div class="neu-field">
        <span class="neu-label">模式</span>
        <div class="neu-chip-row">
          <button
            v-for="item in PRACTICE_MODES"
            :key="item"
            type="button"
            class="neu-chip"
            :class="{ 'is-active': mode === item }"
            @click="mode = item"
          >
            {{ item }}
          </button>
        </div>
      </div>

      <div class="neu-field">
        <span class="neu-label">难度</span>
        <div class="neu-chip-row">
          <button
            v-for="item in DIFFICULTIES"
            :key="item"
            type="button"
            class="neu-chip"
            :class="{ 'is-active': difficulty === item }"
            @click="difficulty = item"
          >
            {{ item }}
          </button>
        </div>
      </div>

      <div class="neu-field">
        <span class="neu-label">病句类型（可选）</span>
        <div class="neu-chip-row">
          <button
            type="button"
            class="neu-chip"
            :class="{ 'is-active': category === '' }"
            @click="category = ''"
          >
            不限
          </button>
          <button
            v-for="item in CATEGORIES"
            :key="item"
            type="button"
            class="neu-chip"
            :class="{ 'is-active': category === item }"
            @click="category = item"
          >
            {{ item }}
          </button>
        </div>
      </div>
    </section>

    <ErrorAlert v-if="errorMessage" :code="errorCode" :message="errorMessage" />
    <p v-if="loading" class="neu-copy">正在加载题库…</p>

    <template v-else>
      <div class="bank-results">
        <div class="bank-results__list neu-list">
          <button
            v-for="item in pageItems"
            :key="item.question_id"
            type="button"
            class="neu-list-item bank-question"
            @click="openQuestion(item)"
          >
            <strong>{{ item.sentence }}</strong>
            <small>{{ item.difficulty }} · {{ item.mode }}</small>
          </button>
          <p v-if="!pageItems.length" class="neu-copy">当前条件下暂无题目。</p>
        </div>

        <div v-if="pool.length" class="bank-results__pager neu-pager">
          <button class="neu-btn" type="button" :disabled="!canPrev || loadingMore" @click="page -= 1">
            上一页
          </button>
          <span class="neu-kicker">第 {{ page }} / {{ totalPages }} 页 · 已载入 {{ pool.length }} 题</span>
          <button class="neu-btn" type="button" :disabled="!canNext || loadingMore" @click="goNext">
            {{ loadingMore ? '加载中…' : '下一页' }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>
