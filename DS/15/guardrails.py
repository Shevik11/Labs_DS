import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

MAX_INPUT = 500
MAX_PROMPT = 1024
MAX_OUTPUT = 64
MAX_STEPS = 1
ALLOWED_TOOLS = frozenset({'retrieve', 'read_graph'})


class Answer(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    answer: str
    status: Literal['answered', 'insufficient_data', 'refused', 'unavailable']
    sources: list[dict]
    graph: list[dict]
    handoff: bool
    reason: str
    confidence: float = Field(ge=0, le=1)
    prompt_tokens: int = Field(ge=0, le=MAX_PROMPT)
    output_tokens: int = Field(ge=0, le=MAX_OUTPUT + 1)
    cache_hit: bool


def refusal(reason, status='refused'):
    return Answer(answer='Потрібна перевірка людиною', status=status,
                  sources=[], graph=[], handoff=True, reason=reason,
                  confidence=0., prompt_tokens=0, output_tokens=0,
                  cache_hit=False).model_dump()


def sensitive(text):
    return bool(re.search(
        r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b(?:sk-|password\s*[=:])\S+|'
        r'(?<![\w.])\+\d[\d ()-]{8,}\d(?![\w.])', text, re.I))


def injection(text):
    return bool(re.search(
        r'ignore.{0,40}instructions|ігноруй|<\s*/?system|SYSTEM:|'
        r'system.{0,20}(prompt|canary)|системн.{0,12}підказ|'
        r'попри обмеження|</user_data>|HACKED', text, re.I | re.S))


class Guarded:
    def __init__(self, engine):
        self.engine = engine

    def ask(self, question, top_k=3, use_graph=True,
            tool='retrieve', steps=1, available=True):
        if tool not in ALLOWED_TOOLS or steps != MAX_STEPS:
            return refusal('autonomy_limit')
        if len(question) > MAX_INPUT or len(question.strip()) < 3:
            return refusal('input_length')
        if injection(question):
            return refusal('prompt_injection')
        if sensitive(question):
            return refusal('private_input')
        if not available:
            return refusal('database_unavailable', 'unavailable')
        try:
            # Live check precedes cache; stale cache never masks DB failure.
            self.engine.health()
            raw = self.engine.ask(question, top_k, use_graph)
            if sensitive(raw['answer']) or any(sensitive(s['quote']) for s in raw['sources']):
                return refusal('private_output')
            if raw['status'] == 'answered':
                # Every citation must point to the retrieved original text.
                for source in raw['sources']:
                    original = next(c for c in self.engine.chunks if c['id'] == source['id'])
                    if source['quote'] not in original['text']:
                        return refusal('invalid_citation')
            payload = {k: raw[k] for k in ('answer','status','sources','graph',
                       'prompt_tokens','output_tokens','cache_hit')}
            payload.update(handoff=raw.get('handoff', False),
                           confidence=raw.get('confidence', 0.),
                           reason='low_confidence' if raw.get('handoff') else 'ok')
            return Answer.model_validate(payload).model_dump()
        except Exception:
            return refusal('backend_or_schema_failure', 'unavailable')
