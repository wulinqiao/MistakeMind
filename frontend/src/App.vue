<script setup>
import { onMounted, ref } from 'vue'
import { fetchStatus } from './api'
const status = ref(null)
onMounted(async () => {
  try { status.value = await fetchStatus() } catch { /* Each page handles request errors. */ }
})
</script>

<template>
  <div class="neu-app">
    <nav class="neu-nav" aria-label="主导航">
      <div class="neu-nav-inner">
        <RouterLink to="/" class="neu-brand" aria-label="MistakeMind 首页">MistakeMind</RouterLink>
        <div class="neu-nav-links">
          <RouterLink class="neu-nav-link" to="/">开始训练</RouterLink>
          <RouterLink class="neu-nav-link" to="/practice">答题</RouterLink>
          <RouterLink class="neu-nav-link" to="/diagnose">句子诊断</RouterLink>
          <RouterLink class="neu-nav-link" to="/history">历史记录</RouterLink>
          <RouterLink class="neu-nav-link" to="/profile">学习画像</RouterLink>
        </div>
      </div>
    </nav>

    <main class="neu-main">
      <p v-if="status?.agent_mode === 'mock' || status?.demo_dataset" class="neu-well neu-copy" role="status">
        {{ status.agent_mode === 'mock' ? '离线演示：诊断只支持固定样例，其他句子需复核。' : '真实模型已连接。' }}
        {{ status.demo_dataset ? '当前题库为开发演示样例，不作为正式教学质量依据。' : '' }}
      </p>
      <p v-if="status && !status.active_questions" class="neu-copy" role="status">暂无已启用练习题。可先使用句子诊断；练习题需审核并导入后开放。</p>
      <RouterView />
    </main>

    <footer class="neu-footer">
      <div class="neu-footer-inner">
        <div>
          <div class="neu-brand">MistakeMind</div>
          <p class="neu-kicker">病句诊断、修改与个性化训练</p>
        </div>
        <div>
          <h2 class="neu-section-title">训练闭环</h2>
          <p class="neu-copy">练习、诊断、提示、讲解、错题记录与复习。</p>
        </div>
      </div>
    </footer>
  </div>
</template>
