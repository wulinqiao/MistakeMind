<script setup>
import { computed, ref, watch } from 'vue'

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
  loading: {
    type: Boolean,
    default: false,
  },
  maxReveals: {
    type: Number,
    default: 3,
  },
})

const collapsed = ref(false)

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

const hasHints = computed(() => texts.value.length > 0)
const emptyConfirmed = computed(() => !props.loading && !hasHints.value)
const revealLimit = computed(() => Math.min(props.maxReveals, texts.value.length))
const canRevealMore = computed(() => props.unlocked && hasHints.value && level.value < revealLimit.value)
const hasRevealed = computed(() => level.value > 0)
const showRevealed = computed(() => hasRevealed.value && !collapsed.value)

const label = computed(() => {
  if (emptyConfirmed.value) return '暂无提示'
  return '分层提示'
})

watch(
  () => [props.hints, props.unlocked],
  () => {
    if (!hasHints.value || !props.unlocked) collapsed.value = false
  },
)

function reveal() {
  if (!canRevealMore.value) return
  collapsed.value = false
  level.value += 1
}

function collapse() {
  if (!hasRevealed.value) return
  collapsed.value = true
}

function expand() {
  if (!hasRevealed.value) return
  collapsed.value = false
}
</script>

<template>
  <section class="neu-stack" style="gap: 12px">
    <div class="hint-actions">
      <button
        type="button"
        class="hint-trigger"
        :class="{
          'is-locked': !unlocked || emptyConfirmed,
          'is-ready': unlocked && hasHints && canRevealMore,
        }"
        :disabled="!canRevealMore"
        :aria-disabled="!canRevealMore"
        @click="reveal"
      >
        <span>{{ label }}</span>
        <span v-if="countdown != null && hasHints" class="hint-countdown">{{ countdown }}s</span>
      </button>

      <button
        v-if="unlocked && hasHints && hasRevealed && !collapsed"
        type="button"
        class="hint-trigger is-ready"
        @click="collapse"
      >
        收起提示
      </button>

      <button
        v-if="unlocked && hasHints && hasRevealed && collapsed"
        type="button"
        class="hint-trigger is-ready"
        @click="expand"
      >
        展开提示
      </button>
    </div>

    <template v-if="showRevealed">
      <p
        v-for="(text, index) in texts.slice(0, level)"
        :key="index"
        class="neu-well neu-hint-text"
      >
        第 {{ index + 1 }} 级：{{ text }}
      </p>
    </template>
  </section>
</template>
