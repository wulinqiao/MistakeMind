<script setup>
defineProps({
  message: { type: String, default: '请求失败，请稍后重试。' },
  code: { type: String, default: '' },
})
</script>

<template>
  <div class="neu-alert" role="alert">
    <span v-if="code" class="neu-accent-text">{{ code }} · </span>{{ message }}
  </div>
</template>
