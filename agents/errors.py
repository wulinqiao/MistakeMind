class ModelError(Exception):
    code = "MODEL_UNAVAILABLE"
    status = 502
    message = "模型配置或服务不可用，请检查本地配置后重试。"


class ModelTimeout(ModelError):
    code = "MODEL_TIMEOUT"
    status = 504
    message = "模型请求超时，请重试。"


class ModelInvalidJSON(ModelError):
    code = "MODEL_INVALID_JSON"
    message = "模型返回未通过结构校验，请重试。"


class ModelUnavailable(ModelError):
    pass


class ModelLowConfidence(ModelError):
    code = "MODEL_LOW_CONFIDENCE"
    status = 200
    message = "本次答案需要补充上下文或人工复核，尚未计入成绩。"


class AnswerValidationError(ValueError):
    pass
