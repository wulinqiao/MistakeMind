<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchProfile } from '../api'
import { USER_ID, messageForError } from '../constants'
import ErrorAlert from '../components/ErrorAlert.vue'

const router = useRouter()
const profile = ref(null)
const loading = ref(false)
const errorCode = ref('')
const errorMessage = ref('')

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

async function load() {
  loading.value = true
  errorCode.value = ''
  errorMessage.value = ''
  try {
    profile.value = await fetchProfile(USER_ID)
  } catch (err) {
    profile.value = null
    errorCode.value = err.code || 'INTERNAL_ERROR'
    errorMessage.value = messageForError(err)
  } finally {
    loading.value = false
  }
}

function practiceCategory(category) {
  router.push({
    path: '/practice',
    query: { mode: '判断题', category },
  })
}

onMounted(load)
</script>

<template>
  <div class="neu-stack">
    <header class="neu-stack">
      <h1 class="neu-section-title">学习画像</h1>
      <p class="neu-copy">{{ profile?.description || '根据近期练习记录推荐复习方向。' }}</p>
    </header>

    <div class="neu-actions">
      <button class="neu-btn" type="button" :disabled="loading" @click="load">刷新画像</button>
    </div>

    <ErrorAlert v-if="errorMessage" :code="errorCode" :message="errorMessage" />
    <p v-if="loading" class="neu-copy">加载中…</p>

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

      <section v-if="profile.recommended_categories?.length" class="neu-stack" style="gap: 12px">
        <h2 class="neu-section-title">推荐知识点</h2>
        <p class="neu-copy">推荐同时考虑近期错题与新类型探索，未练过的类型不表示已经判断为薄弱项。</p>
        <div class="neu-chip-row">
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
      </section>

      <section class="neu-stack" style="gap: 12px">
        <h2 class="neu-section-title">近期练习表现</h2>
        <p class="neu-copy">基于最近 {{ profile.recent_window }} 次作答进行平滑估计；每类至少 {{ profile.minimum_samples }} 次后再判断复习优先级。</p>
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
              · 错误 {{ item.errors }} 次
            </p>
            <div class="neu-bar-track" :aria-label="`${item.category} 掌握度`">
              <div
                class="neu-bar-fill"
                :style="{ width: `${Math.round((Number(item.mastery || 0) / maxMastery) * 100)}%` }"
              />
            </div>
            <div class="neu-actions" style="margin-top: 4px">
              <button class="neu-btn" type="button" @click="practiceCategory(item.category)">
                练习该类型
              </button>
            </div>
          </article>
          <p v-if="!(profile.category_stats || []).length" class="neu-copy">
            暂无分类统计，完成几道练习后再来查看。
          </p>
        </div>
      </section>

      <section v-if="profile.trend?.length" class="neu-stack">
        <h2 class="neu-section-title">每日练习趋势</h2>
        <table class="neu-table">
          <thead><tr><th>日期</th><th>题数</th><th>正确率</th></tr></thead>
          <tbody><tr v-for="day in profile.trend" :key="day.date"><td>{{ day.date }}</td><td>{{ day.attempts }}</td><td><meter min="0" max="1" :value="day.accuracy" :aria-label="`${day.date} 正确率`" /> {{ Math.round(day.accuracy * 100) }}%</td></tr></tbody>
        </table>
      </section>

      <p v-if="profile.next_review_at" class="neu-kicker">
        下次复习建议：{{ profile.next_review_at }}
      </p>
    </template>
  </div>
</template>
