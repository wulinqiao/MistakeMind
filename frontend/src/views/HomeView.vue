<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchProfile, fetchQuestions } from '../api'
import { CATEGORIES, USER_ID, messageForError } from '../constants'
import { attemptRevision } from '../refreshSignal'
import ErrorAlert from '../components/ErrorAlert.vue'
import MarqueeStrip from '../components/MarqueeStrip.vue'

defineOptions({ name: 'HomeView' })

/** 推荐跑马灯：up | down | left | right */
const MARQUEE_DIRECTION = 'up'
/** 推荐跑马灯速度（px/s） */
const MARQUEE_SPEED = 36
/** 竖向可视条数 */
const MARQUEE_VISIBLE = 3

const router = useRouter()
const questions = ref([])
const profile = ref(null)
const loadingQuestions = ref(false)
const loadingProfile = ref(false)
const questionError = ref('')
const questionErrorCode = ref('')
const profileError = ref('')
const profileErrorCode = ref('')

const priorityLabel = {
  insufficient: '样本较少，继续积累',
  high: '优先复习',
  medium: '保持练习',
  low: '巩固',
}

const maxMastery = computed(() => {
  const stats = profile.value?.category_stats || []
  const values = stats.map((item) => Number(item.mastery || 0))
  return Math.max(1, ...values)
})

async function fetchOneByCategory(category) {
  try {
    const data = await fetchQuestions({ category, count: 1 })
    const item = data.questions?.[0]
    return item ? { ...item, category } : null
  } catch {
    return null
  }
}

async function loadCatalogPicks() {
  const picks = await Promise.all(CATEGORIES.map((category) => fetchOneByCategory(category)))
  const seen = new Set()
  return picks.filter((item) => {
    if (!item?.question_id || seen.has(item.question_id)) return false
    seen.add(item.question_id)
    return true
  })
}

async function loadQuestions(profileData) {
  loadingQuestions.value = true
  questionError.value = ''
  questionErrorCode.value = ''
  try {
    const hasHistory = Number(profileData?.total_attempts || 0) > 0
    if (!hasHistory) {
      questions.value = await loadCatalogPicks()
    } else {
      const data = await fetchQuestions({ count: 10, user_id: USER_ID })
      questions.value = data.questions || []
      if (!questions.value.length) {
        questions.value = await loadCatalogPicks()
      }
    }
  } catch (err) {
    questions.value = []
    questionErrorCode.value = err.code || 'INTERNAL_ERROR'
    questionError.value = messageForError(err)
  } finally {
    loadingQuestions.value = false
  }
}

async function loadProfile() {
  loadingProfile.value = true
  profileError.value = ''
  profileErrorCode.value = ''
  try {
    profile.value = await fetchProfile(USER_ID)
  } catch (err) {
    profile.value = null
    profileErrorCode.value = err.code || 'INTERNAL_ERROR'
    profileError.value = messageForError(err)
  } finally {
    loadingProfile.value = false
  }
  return profile.value
}

function startPractice() {
  router.push({ path: '/practice' })
}

function openQuestion(item) {
  sessionStorage.setItem('mm_last_question_id', item.question_id)
  router.push({
    path: '/practice/question',
    query: {
      question_id: item.question_id,
      ...(item.mode ? { mode: item.mode } : {}),
    },
  })
}

function practiceCategory(category) {
  router.push({
    path: '/practice',
    query: { mode: '判断题', category },
  })
}

async function refreshAfterAttempt() {
  const profileData = await loadProfile()
  await loadQuestions(profileData)
}

onMounted(async () => {
  await refreshAfterAttempt()
})

watch(attemptRevision, () => {
  refreshAfterAttempt()
})
</script>

<template>
  <div class="neu-stack">
    <section class="neu-hero">
      <h1>MistakeMind</h1>
      <p class="neu-lead">
        判断对错只是开始。定位错误、分层提示、最小修改，再根据薄弱类型继续练。
      </p>
      <div class="neu-actions">
        <RouterLink class="neu-btn neu-btn-primary" to="/diagnose">诊断一句话</RouterLink>
        <button class="neu-btn" type="button" @click="startPractice">开始答题</button>
      </div>
    </section>

    <section class="neu-stack">
      <h2 class="neu-section-title">推荐题目</h2>

      <ErrorAlert v-if="questionError" :code="questionErrorCode" :message="questionError" />
      <p v-if="loadingQuestions" class="neu-copy">正在加载推荐题…</p>
      <MarqueeStrip
        v-else-if="questions.length"
        :key="questions.map((item) => item.question_id).join('|')"
        class="home-recommend-marquee"
        :direction="MARQUEE_DIRECTION"
        :speed="MARQUEE_SPEED"
        :visible-count="MARQUEE_VISIBLE"
      >
        <button
          v-for="item in questions"
          :key="item.question_id"
          type="button"
          class="neu-list-item bank-question"
          @click="openQuestion(item)"
        >
          <strong>{{ item.sentence }}</strong>
          <small>
            {{ item.difficulty }} · {{ item.mode }}
            <template v-if="item.category"> · {{ item.category }}</template>
          </small>
        </button>
      </MarqueeStrip>
      <p v-else class="neu-copy">暂无推荐题。可先去题库选题，或完成几次练习后再来。</p>
    </section>

    <section class="neu-stack">
      <header class="neu-stack" style="gap: 8px">
        <h2 class="neu-section-title">学习画像</h2>
      </header>

      <div class="neu-actions">
        <RouterLink class="neu-btn" to="/profile">查看完整画像</RouterLink>
      </div>

      <ErrorAlert v-if="profileError" :code="profileErrorCode" :message="profileError" />
      <p v-if="loadingProfile" class="neu-copy">加载中…</p>

      <template v-else-if="profile">
        <div class="neu-grid neu-grid-3">
          <div class="neu-stat">
            <strong>{{ profile.total_attempts }}</strong>
            <span>累计作答</span>
          </div>
          <div class="neu-stat">
            <strong>{{ Math.round((profile.overall_accuracy || 0) * 100) }}%</strong>
            <span>总正确率</span>
          </div>
          <div class="neu-stat">
            <strong>{{ profile.recommended_categories?.[0] || '暂无' }}</strong>
            <span>推荐练习类型</span>
          </div>
        </div>

        <div v-if="profile.recommended_categories?.length" class="neu-chip-row">
          <button
            v-for="item in profile.recommended_categories"
            :key="item"
            type="button"
            class="neu-chip is-active"
            @click="practiceCategory(item)"
          >
            {{ item }}
          </button>
        </div>

        <div class="neu-list">
          <article
            v-for="item in profile.category_stats || []"
            :key="item.category"
            class="neu-list-item"
          >
            <div class="neu-bar-head">
              <strong>{{ item.category }}</strong>
              <span class="neu-kicker">{{ priorityLabel[item.priority] || item.priority || '继续练习' }}</span>
            </div>
            <p>
              正确率 {{ Math.round((item.accuracy || 0) * 100) }}%
              （{{ item.correct }}/{{ item.attempts }}）
              · 近期平滑正确率 {{ Math.round((item.mastery || 0) * 100) }}%
            </p>
            <div class="neu-bar-track" :aria-label="`${item.category} 掌握度`">
              <div
                class="neu-bar-fill"
                :style="{ width: `${Math.round((Number(item.mastery || 0) / maxMastery) * 100)}%` }"
              />
            </div>
          </article>
          <p v-if="!(profile.category_stats || []).length" class="neu-copy">
            暂无分类统计，完成几道练习后再来查看。
          </p>
        </div>
      </template>
    </section>

    <section class="neu-stack">
      <h2 class="neu-section-title">三种题型</h2>
      <div class="neu-grid neu-grid-3">
        <article class="neu-card">
          <h3>判断题</h3>
          <p>先判断是不是病句，再看错误类型和位置。</p>
        </article>
        <article class="neu-card">
          <h3>选择题</h3>
          <p>在选项中找出正确判断或更合适的改法。</p>
        </article>
        <article class="neu-card">
          <h3>修改题</h3>
          <p>自己改写句子，尽量少改字并保持原意。</p>
        </article>
      </div>
    </section>
  </div>
</template>
