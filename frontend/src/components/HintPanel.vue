<script setup>
import { computed } from 'vue'

const level = defineModel('level', { type: Number, default: 0 })

const props = defineProps({
  hints: {
    type: Array,
    default: () => [],
  },
  unlocked: {
    type: Boolean,
    default: true,
  },
  countdown: {
    type: Number,
    default: null,
  },
  maxReveals: {
    type: Number,
    default: 3,
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

const revealLimit = computed(() => Math.min(props.maxReveals, texts.value.length))
const canReveal = computed(() => props.unlocked && level.value < revealLimit.value)
const revealed = computed(() => texts.value.slice(0, level.value))

function reveal() {
  if (!canReveal.value) return
  level.value += 1
}
</script>

<template>
  <section class="neu-stack" style="gap: 12px">
    <button
      type="button"
      class="hint-trigger"
      :class="{ 'is-locked': !unlocked, 'is-ready': unlocked }"
      :disabled="!canReveal"
      @click="reveal"
    >
      <span>分层提示</span>
      <span v-if="countdown != null" class="hint-countdown">{{ countdown }}s</span>
      <span v-else-if="unlocked && level < revealLimit" class="hint-meta">
        还可点 {{ revealLimit - level }} 次
      </span>
      <span v-else-if="unlocked" class="hint-meta">已展开</span>
    </button>

    <p
      v-for="(text, index) in revealed"
      :key="index"
      class="neu-well neu-hint-text"
    >
      第 {{ index + 1 }} 级：{{ text }}
    </p>
  </section>
</template>
