<script setup>
import { computed, ref, watch } from 'vue'
import { fetchHistory } from '../api'
import { CATEGORIES, USER_ID, messageForError } from '../constants'
import ErrorAlert from '../components/ErrorAlert.vue'

const filters = ['全部', ...CATEGORIES]
const current = ref('全部')
const page = ref(1)
const pageSize = 20
const total = ref(0)
const items = ref([])
const loading = ref(false)
const errorCode = ref('')
const errorMessage = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize) || 1))

async function load() {
  loading.value = true
  errorCode.value = ''
  errorMessage.value = ''
  try {
    const data = await fetchHistory(USER_ID, {
      page: page.value,
      page_size: pageSize,
      category: current.value === '全部' ? undefined : current.value,
    })
    items.value = data.items || []
    total.value = data.total || 0
    page.value = data.page || page.value
  } catch (err) {
    items.value = []
    total.value = 0
    errorCode.value = err.code || 'INTERNAL_ERROR'
    errorMessage.value = messageForError(err)
  } finally {
    loading.value = false
  }
}

function selectCategory(category) {
  current.value = category
  page.value = 1
}

watch([current, page], load, { immediate: true })
</script>

<template>
  <div class="neu-stack">
    <header class="neu-stack">
      <h1 class="neu-section-title">历史记录</h1>
      <p class="neu-copy">按病句类型筛选作答记录，数据来自后端历史接口。</p>
    </header>

    <div class="neu-chip-row">
      <button
        v-for="category in filters"
        :key="category"
        type="button"
        class="neu-chip"
        :class="{ 'is-active': current === category }"
        @click="selectCategory(category)"
      >
        {{ category }}
      </button>
    </div>

    <ErrorAlert v-if="errorMessage" :code="errorCode" :message="errorMessage" />
    <p v-if="loading" class="neu-copy">加载中…</p>

    <div v-else class="neu-list">
      <article v-for="item in items" :key="item.attempt_id" class="neu-list-item">
        <strong :class="item.is_correct ? 'neu-ok' : 'neu-bad'">
          {{ item.is_correct ? '正确' : '错误' }}
        </strong>
        <p>
          题目 {{ item.question_id }} · 作答：{{ item.answer }}
          <template v-if="item.error_types?.length"> · {{ item.error_types.join('、') }}</template>
        </p>
        <small>{{ item.created_at }} · {{ item.attempt_id }}</small>
      </article>
      <p v-if="!items.length" class="neu-copy">暂无记录。可先去答题或诊断创建用户。</p>
    </div>

    <div class="neu-pager">
      <button class="neu-btn" type="button" :disabled="page <= 1 || loading" @click="page -= 1">
        上一页
      </button>
      <span class="neu-kicker">第 {{ page }} / {{ totalPages }} 页 · 共 {{ total }} 条</span>
      <button
        class="neu-btn"
        type="button"
        :disabled="page * pageSize >= total || loading"
        @click="page += 1"
      >
        下一页
      </button>
    </div>
  </div>
</template>
