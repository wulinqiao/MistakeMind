"""Compatibility facade for D's API; implementation belongs to B's agents package."""
import uuid

from agents.config import Settings
from agents.errors import ModelError, ModelInvalidJSON, ModelLowConfidence, ModelTimeout, ModelUnavailable
from agents.pipeline import AgentService
from schemas.models import AgentContext


def diagnose(sentence: str, need_hints: bool = True, *, grade=None, optional_context=None,
             request_id=None, user_id="anonymous"):
    ctx = AgentContext(request_id=request_id or "req_" + uuid.uuid4().hex[:12], user_id=user_id,
                       task="diagnose", sentence=sentence, grade=grade,
                       optional_context=optional_context, need_hints=need_hints)
    return AgentService().diagnose(ctx)


def mock_diagnose(sentence: str, need_hints: bool = True):
    return AgentService(Settings(mode="mock")).diagnose(AgentContext(
        request_id="demo", user_id="anonymous", task="diagnose", sentence=sentence, need_hints=need_hints))


def grade_answer(ctx, question, answer_type):
    return AgentService().grade(ctx, question, answer_type)
