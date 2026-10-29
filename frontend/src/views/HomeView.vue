<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { CATEGORIES, DIFFICULTIES, PRACTICE_MODES } from '../constants'

const router = useRouter()
const mode = ref('判断题')
const difficulty = ref('初中')
const category = ref('')

function startPractice() {
  router.push({
    path: '/practice',
    query: {
      mode: mode.value,
      difficulty: difficulty.value || undefined,
      category: category.value || undefined,
    },
  })
}
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
