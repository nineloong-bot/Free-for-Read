import os
from typing import Protocol


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
    @property
    def dimension(self) -> int: ...


class StubEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in texts]

    @property
    def dimension(self) -> int:
        return 384


class LocalEmbeddingProvider:
    def __init__(self, model_name: str = "BAAI/bge-small-zh"):
        self._model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        result = model.encode(texts, normalize_embeddings=True)
        return result.tolist()

    @property
    def dimension(self) -> int:
        return 512


class OpenAIEmbeddingProvider:
    def __init__(self, api_key: str | None = None, model: str = "text-embedding-3-small"):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        from openai import OpenAI
        client = OpenAI(api_key=self._api_key)
        resp = client.embeddings.create(model=self._model, input=texts)
        return [d.embedding for d in resp.data]

    @property
    def dimension(self) -> int:
        return 1536


def create_embedding_provider(provider: str = "local", **kwargs) -> EmbeddingProvider:
    if provider == "local":
        return LocalEmbeddingProvider(**kwargs)
    if provider == "openai":
        return OpenAIEmbeddingProvider(**kwargs)
    if provider == "stub":
        return StubEmbeddingProvider()
    raise ValueError(f"Unknown embedding provider: {provider}")
