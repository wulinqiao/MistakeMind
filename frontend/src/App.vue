<script setup>
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
