<script setup>
import { computed } from 'vue'

const level = defineModel('level', { type: Number, default: 0 })

const props = defineProps({
  hints: {
    type: Array,
    default: () => [],
  },
})

const ordered = computed(() =>
  [...props.hints].sort((a, b) => {
    const la = typeof a === 'object' && a?.level != null ? Number(a.level) : 0
    const lb = typeof b === 'object' && b?.level != null ? Number(b.level) : 0
    return la - lb
  }),
)

const texts = computed(() =>
  ordered.value.map((item) => (typeof item === 'string' ? item : item.text)).filter(Boolean),
)

function reveal() {
  if (level.value < texts.value.length) level.value += 1
}
</script>

<template>
  <section v-if="texts.length" class="neu-stack">
    <div class="neu-actions">
      <button class="neu-btn" type="button" :disabled="level >= texts.length" @click="reveal">
        {{ level === 0 ? '查看提示' : '下一级提示' }}
      </button>
    </div>
    <p v-if="level > 0" class="neu-well neu-hint-text">
      第 {{ level }} 级：{{ texts[level - 1] }}
    </p>
  </section>
</template>
