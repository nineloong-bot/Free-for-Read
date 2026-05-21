from free_for_read.ai.embeddings import create_embedding_provider


class StubEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 384 for _ in texts]

    @property
    def dimension(self) -> int:
        return 384


def test_embedding_provider_interface() -> None:
    provider = StubEmbeddingProvider()
    result = provider.embed(["hello", "world"])
    assert len(result) == 2
    assert len(result[0]) == 384
    assert provider.dimension == 384


def test_create_embedding_provider_stub() -> None:
    provider = create_embedding_provider("stub")
    assert provider.dimension > 0
    result = provider.embed(["test"])
    assert len(result) == 1
    assert len(result[0]) == provider.dimension
