<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { loadPracticeSession } from '../practiceSession'

defineOptions({ name: 'PracticeLayout' })

const route = useRoute()

const bankLink = computed(() => {
  const session = loadPracticeSession()
  const mode = typeof route.query.mode === 'string'
    ? route.query.mode
    : session.mode || sessionStorage.getItem('mm_bank_mode') || undefined
  const difficulty = typeof route.query.difficulty === 'string'
    ? route.query.difficulty
    : session.difficulty || sessionStorage.getItem('mm_bank_difficulty') || undefined
  const category = typeof route.query.category === 'string'
    ? route.query.category
    : session.category || sessionStorage.getItem('mm_bank_category') || undefined

  return {
    path: '/practice',
    query: {
      ...(mode ? { mode } : {}),
      ...(difficulty ? { difficulty } : {}),
      ...(category ? { category } : {}),
    },
  }
})

const questionLink = computed(() => {
  const session = loadPracticeSession()
  const qid = typeof route.query.question_id === 'string'
    ? route.query.question_id
    : session.questionDraft?.question_id || sessionStorage.getItem('mm_last_question_id')
  const mode = typeof route.query.mode === 'string'
    ? route.query.mode
    : session.mode || sessionStorage.getItem('mm_bank_mode') || undefined
  const difficulty = typeof route.query.difficulty === 'string'
    ? route.query.difficulty
    : session.difficulty || sessionStorage.getItem('mm_bank_difficulty') || undefined
  const category = typeof route.query.category === 'string'
    ? route.query.category
    : session.category || sessionStorage.getItem('mm_bank_category') || undefined

  return {
    path: '/practice/question',
    query: {
      ...(qid ? { question_id: qid } : {}),
      ...(mode ? { mode } : {}),
      ...(difficulty ? { difficulty } : {}),
      ...(category ? { category } : {}),
    },
  }
})
</script>

<template>
  <div class="practice-shell">
    <aside class="practice-sidebar" aria-label="答题侧栏">
      <RouterLink
        class="practice-side-box"
        :class="{ 'is-active': route.path === '/practice' }"
        :to="bankLink"
      >
        题库
      </RouterLink>
      <RouterLink
        class="practice-side-box"
        :class="{ 'is-active': route.path.startsWith('/practice/question') }"
        :to="questionLink"
      >
        题目
      </RouterLink>
    </aside>
    <div class="practice-panel">
      <RouterView v-slot="{ Component }">
        <KeepAlive :max="2">
          <component :is="Component" />
        </KeepAlive>
      </RouterView>
    </div>
  </div>
</template>
