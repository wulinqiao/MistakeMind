export const USER_ID = 'user_001'

export const CATEGORIES = [
  '成分残缺',
  '成分赘余',
  '搭配不当',
  '语序不当',
  '结构混乱',
  '表意不明',
  '不合逻辑',
  '关联词使用不当',
  '其他',
]

export const DIFFICULTIES = ['小学高年级', '初中', '高中', '综合']

export const PRACTICE_MODES = ['判断题', '选择题', '修改题']

export const ERROR_MESSAGES = {
  VALIDATION_ERROR: '请求字段有误，请检查后重试。',
  QUESTION_NOT_FOUND: '题目不存在或已下线。',
  USER_NOT_FOUND: '用户不存在，请先完成一次诊断或答题。',
  MODEL_TIMEOUT: '模型请求超时，请稍后重试。',
  MODEL_INVALID_JSON: '模型返回异常，请稍后重试。',
  MODEL_LOW_CONFIDENCE: '模型置信度较低，结果仅供参考。',
  DATABASE_ERROR: '数据读写失败，请稍后重试。',
  INTERNAL_ERROR: '服务内部错误，请稍后重试。',
  NETWORK_ERROR: '无法连接后端，请确认服务已启动。',
}

export function messageForError(error) {
  if (!error) return ERROR_MESSAGES.INTERNAL_ERROR
  if (error.message) return error.message
  return ERROR_MESSAGES[error.code] || ERROR_MESSAGES.INTERNAL_ERROR
}
