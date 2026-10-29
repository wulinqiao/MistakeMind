<script setup>
defineProps({
  diagnosis: {
    type: Object,
    default: () => ({
      has_error: true,
      error_types: [],
      error_span: null,
      explanation: '',
      corrections: [],
    }),
  },
  showHintsSummary: { type: Boolean, default: false },
})
</script>

<template>
  <article class="neu-card">
    <h3>诊断结果</h3>
    <p v-if="diagnosis.original_sentence" class="neu-result-block">
      原句：{{ diagnosis.original_sentence }}
    </p>
    <p class="neu-result-block">
      {{ diagnosis.has_error ? '判定：存在语病' : '判定：不是病句' }}
    </p>
    <p v-if="diagnosis.error_types?.length" class="neu-result-block">
      病句类型：{{ diagnosis.error_types.join('、') }}
    </p>
    <p v-if="diagnosis.error_span" class="neu-result-block">
      错误位置：{{ diagnosis.error_span }}
    </p>
    <p v-if="diagnosis.explanation" class="neu-result-block">
      {{ diagnosis.explanation }}
    </p>
    <div v-if="diagnosis.corrections?.length" class="neu-stack" style="gap: 12px">
      <div
        v-for="(item, index) in diagnosis.corrections"
        :key="index"
        class="neu-well"
      >
        <p class="neu-result-block">
          修改{{ diagnosis.corrections.length > 1 ? ` ${index + 1}` : '' }}：
          {{ typeof item === 'string' ? item : item.text }}
          <template v-if="item?.kind">（{{ item.kind }}）</template>
        </p>
        <p v-if="item?.reason" class="neu-kicker">理由：{{ item.reason }}</p>
      </div>
    </div>
    <p v-if="showHintsSummary && diagnosis.hints?.length" class="neu-result-block">
      提示：{{ diagnosis.hints.map((h) => h.text || h).join('；') }}
    </p>
    <p v-if="diagnosis.confidence != null" class="neu-kicker">
      置信度：{{ Number(diagnosis.confidence).toFixed(2) }}
      <template v-if="diagnosis.review_status"> · 复核：{{ diagnosis.review_status }}</template>
    </p>
    <p v-else-if="diagnosis.review_status" class="neu-kicker">
      复核：{{ diagnosis.review_status }}
    </p>
  </article>
</template>
