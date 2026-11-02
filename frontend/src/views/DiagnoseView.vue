<script setup>
import { ref } from 'vue'
import { diagnoseSentence } from '../api'
import { USER_ID, messageForError } from '../constants'
import DiagnosisCard from '../components/DiagnosisCard.vue'
import ErrorAlert from '../components/ErrorAlert.vue'

defineOptions({ name: 'DiagnoseView' })

const sentence = ref('通过开展此次活动，使同学们提高了环保意识。')
const optionalContext = ref('')
const loading = ref(false)
const diagnosis = ref(null)
const errorCode = ref('')
const errorMessage = ref('')

async function diagnose() {
  errorCode.value = ''
  errorMessage.value = ''
  diagnosis.value = null

  if (!sentence.value.trim()) {
    errorCode.value = 'VALIDATION_ERROR'
    errorMessage.value = 'sentence 不能为空'
    return
  }

  loading.value = true
  try {
    diagnosis.value = await diagnoseSentence({
      sentence: sentence.value.trim(),
      user_id: USER_ID,
      grade: '初中',
      optional_context: optionalContext.value.trim() || null,
      need_hints: false,
    })
  } catch (err) {
    errorCode.value = err.code || 'INTERNAL_ERROR'
    errorMessage.value = messageForError(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="neu-stack">
    <header class="neu-stack">
      <h1 class="neu-section-title">句子诊断</h1>
      <p class="neu-copy">输入一句话，查看病句类型、错误位置、解释和修改建议。</p>
    </header>

    <label class="neu-field">
      <span class="neu-label">待诊断句子</span>
      <textarea v-model="sentence" class="neu-textarea" maxlength="500" />
    </label>

    <label class="neu-field">
      <span class="neu-label">补充说明（可选）</span>
      <textarea
        v-model="optionalContext"
        class="neu-textarea"
        maxlength="500"
        placeholder="例如：不确定主语在哪里"
      />
    </label>

    <div class="neu-actions">
      <button class="neu-btn neu-btn-primary" type="button" :disabled="loading" @click="diagnose">
        {{ loading ? '诊断中…' : '开始诊断' }}
      </button>
    </div>

    <ErrorAlert v-if="errorMessage" :code="errorCode" :message="errorMessage" />

    <template v-if="diagnosis">
      <p
        v-if="diagnosis.review_status === 'needs_review' || Number(diagnosis.confidence) < 0.6"
        class="neu-alert"
        role="status"
      >
        模型置信度较低或待复核，结果仅供参考。
      </p>
      <DiagnosisCard :diagnosis="diagnosis" />
    </template>
  </div>
</template>
