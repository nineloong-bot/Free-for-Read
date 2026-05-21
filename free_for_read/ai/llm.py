import os
from typing import Literal, Protocol

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LlmProvider(Protocol):
    async def chat(self, messages: list[ChatMessage], *, max_tokens: int = 1024) -> str: ...


class StubLlmProvider:
    async def chat(self, messages: list[ChatMessage], *, max_tokens: int = 1024) -> str:
        return f"Stub response to: {messages[-1].content[:50]}"


class OpenAiLlmProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
    ):
        key = api_key or os.environ.get("AI_API_KEY")
        self._api_key = key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model
        self._base_url = base_url or os.environ.get("AI_BASE_URL")

    async def chat(self, messages: list[ChatMessage], *, max_tokens: int = 1024) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        resp = await client.chat.completions.create(
            model=self._model,
            messages=[m.model_dump() for m in messages],
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""


class AnthropicLlmProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-3-haiku-20240307",
    ):
        key = api_key or os.environ.get("AI_API_KEY")
        self._api_key = key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._model = model

    async def chat(self, messages: list[ChatMessage], *, max_tokens: int = 1024) -> str:
        from anthropic import AsyncAnthropic
        system = next((m.content for m in messages if m.role == "system"), None)
        chat_messages = [m.model_dump() for m in messages if m.role != "system"]
        client = AsyncAnthropic(api_key=self._api_key)
        kwargs = {"model": self._model, "max_tokens": max_tokens, "messages": chat_messages}
        if system:
            kwargs["system"] = system
        resp = await client.messages.create(**kwargs)
        block = resp.content[0]
        return block.text if hasattr(block, "text") else str(block)


class OllamaLlmProvider:
    def __init__(self, model: str = "qwen2.5:7b", base_url: str | None = None):
        self._model = model
        self._base_url = (
            base_url
            or os.environ.get("AI_BASE_URL")
            or os.environ.get("OLLAMA_HOST")
            or "http://localhost:11434"
        )

    async def chat(self, messages: list[ChatMessage], *, max_tokens: int = 1024) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(base_url=f"{self._base_url}/v1", api_key="ollama")
        resp = await client.chat.completions.create(
            model=self._model,
            messages=[m.model_dump() for m in messages],
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""


def create_llm_provider(provider: str = "openai", **kwargs) -> LlmProvider:
    if provider == "openai":
        return OpenAiLlmProvider(**kwargs)
    if provider == "anthropic":
        return AnthropicLlmProvider(**kwargs)
    if provider == "ollama":
        return OllamaLlmProvider(**kwargs)
    if provider == "stub":
        return StubLlmProvider()
    raise ValueError(f"Unknown LLM provider: {provider}")
