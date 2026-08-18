from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from app.schemas import EvaluationResult, TutorResponse, TutorUIBlock

T = TypeVar("T", bound=BaseModel)


class LLMProvider(Protocol):
    async def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str: ...
    async def generate_structured(self, messages: list[dict[str, str]], schema: type[T], **kwargs: Any) -> T: ...
    async def stream(self, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[str]: ...


class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class STTProvider(Protocol):
    async def transcribe(self, audio: bytes) -> str: ...


class TTSProvider(Protocol):
    async def synthesize(self, text: str) -> bytes: ...


class MockLLMProvider:
    async def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        user_text = messages[-1]["content"] if messages else ""
        return self._reply(user_text)

    async def generate_structured(self, messages: list[dict[str, str]], schema: type[T], **kwargs: Any) -> T:
        if schema is EvaluationResult:
            text = messages[-1]["content"].lower()
            technical = .84 if any(word in text for word in ("api", "cache", "database", "authorization", "latency")) else .62
            grammar = .62 if "i've" in text and "yesterday" in text else .82
            errors = [] if grammar > .7 else [{"error_type":"present-perfect-vs-past-simple","original":"I've ... yesterday","corrected":"I ... yesterday","explanation":"Use Past Simple with a finished time marker."}]
            return schema.model_validate({"technical_correctness":technical,"grammar_accuracy":grammar,"vocabulary_range":.76,"technical_vocabulary":technical,"clarity":.78,"task_completion":.85,"confidence":.86,"errors":errors})
        return schema.model_validate({})

    async def stream(self, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        for word in self._reply(messages[-1]["content"]).split(" "):
            await asyncio.sleep(.018)
            yield word + " "

    @staticmethod
    def _reply(text: str) -> str:
        lowered = text.lower()
        if "authentication" in lowered or "authorization" in lowered:
            return "Good distinction to practise. Authentication answers ‘Who are you?’, while authorization answers ‘What are you allowed to do?’. Now give me a concrete API example using both terms."
        if "latency" in lowered or "performance" in lowered:
            return "That is a useful direction. Make the explanation interview-ready: state the bottleneck, describe the change, then quantify the result. For example: ‘We identified an N+1 query, added eager loading, and reduced p95 latency by 35%.’ What trade-off did your solution introduce?"
        if "deploy" in lowered or "production" in lowered:
            return "Nice. In team communication, say ‘deploy to production’ rather than ‘deploy on production’. Tell me what checks you completed before the release and how you would roll it back."
        return "Let’s turn that into precise technical English. Start with the context, name the technical decision, and explain its impact. Can you add one measurable detail and one trade-off?"

    def tutor_response(self, text: str) -> TutorResponse:
        reply = self._reply(text)
        blocks = []
        if "deploy" in text.lower():
            blocks.append(TutorUIBlock(type="VOCAB_CARD", payload={"term":"deploy to production","meaning":"make a release available in the production environment","example":"We deployed the new API to production."}))
        return TutorResponse(message=reply, ui_blocks=blocks, suggested_actions=["Give a concrete example", "Practice an interview answer"])


class MockEmbeddingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[(sum(map(ord, text[i::8])) % 997) / 997 for i in range(8)] for text in texts]


class OpenAILLMProvider:
    def __init__(self, api_key: str, model: str):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        response = await self.client.responses.create(model=self.model, input=messages, **kwargs)
        return response.output_text

    async def generate_structured(self, messages: list[dict[str, str]], schema: type[T], **kwargs: Any) -> T:
        response = await self.client.responses.parse(model=self.model, input=messages, text_format=schema, **kwargs)
        return response.output_parsed

    async def stream(self, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        stream = await self.client.responses.create(model=self.model, input=messages, stream=True, **kwargs)
        async for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta

