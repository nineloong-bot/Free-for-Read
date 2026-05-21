import pytest

from free_for_read.ai.llm import ChatMessage, create_llm_provider


class StubLlmProvider:
    async def chat(self, messages: list[ChatMessage], *, max_tokens: int = 1024) -> str:
        return f"Stub response to: {messages[-1].content[:30]}"


def test_chat_message_model() -> None:
    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"


@pytest.mark.asyncio
async def test_stub_llm_provider() -> None:
    provider = StubLlmProvider()
    result = await provider.chat([ChatMessage(role="user", content="What is this?")])
    assert "Stub response" in result


def test_create_llm_provider_stub() -> None:
    provider = create_llm_provider("stub")
    assert hasattr(provider, 'chat')
