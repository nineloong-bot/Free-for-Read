from pathlib import Path

import chromadb

from free_for_read.ai.embeddings import EmbeddingProvider


class BookIndexer:
    def __init__(self, *, chroma_path: Path, embeddings: EmbeddingProvider):
        self._client = chromadb.PersistentClient(path=str(chroma_path))
        self._embeddings = embeddings

    def _collection_name(self, book_id: str) -> str:
        return f"book_{book_id}"

    def index_book(self, book_id: str, chunks: list[dict]) -> None:
        name = self._collection_name(book_id)
        try:
            self._client.delete_collection(name)
        except Exception:
            pass

        if not chunks:
            return

        collection = self._client.create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

        texts = [c["text"] for c in chunks]
        ids = [c["id"] for c in chunks]
        embeddings = self._embeddings.embed(texts)
        metadatas = [
            {
                "chapter_id": c.get("chapter_id", ""),
                "chapter_title": c.get("chapter_title", ""),
                "heading_path": c.get("heading_path", ""),
            }
            for c in chunks
        ]

        collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

    def query(
        self,
        book_id: str,
        query_text: str,
        *,
        top_k: int = 5,
        chapter_id: str | None = None,
    ) -> list[dict]:
        name = self._collection_name(book_id)
        try:
            collection = self._client.get_collection(name)
        except Exception:
            return []

        query_embedding = self._embeddings.embed([query_text])
        query_kwargs = {"query_embeddings": query_embedding, "n_results": top_k}
        if chapter_id:
            query_kwargs["where"] = {"chapter_id": chapter_id}
        results = collection.query(**query_kwargs)

        output: list[dict] = []
        if results["ids"] and results["ids"][0]:
            docs = results.get("documents", [[]])
            metas = results.get("metadatas", [[]])
            dists = results.get("distances", [[]])
            for i, doc_id in enumerate(results["ids"][0]):
                meta = metas[0][i] if metas and metas[0] else {}
                output.append({
                    "id": doc_id,
                    "text": docs[0][i] if docs and docs[0] else "",
                    "chapter_id": meta.get("chapter_id", ""),
                    "chapter_title": meta.get("chapter_title", ""),
                    "heading_path": meta.get("heading_path", ""),
                    "score": 1.0 - (dists[0][i] if dists and dists[0] else 0.0),
                })
        return output

    def documents(self, book_id: str, *, chapter_id: str | None = None) -> list[dict]:
        name = self._collection_name(book_id)
        try:
            collection = self._client.get_collection(name)
        except Exception:
            return []

        get_kwargs = {}
        if chapter_id:
            get_kwargs["where"] = {"chapter_id": chapter_id}
        results = collection.get(**get_kwargs)
        ids = results.get("ids") or []
        docs = results.get("documents") or []
        metas = results.get("metadatas") or []

        output: list[dict] = []
        for index, doc_id in enumerate(ids):
            meta = metas[index] if index < len(metas) and metas[index] else {}
            output.append({
                "id": doc_id,
                "text": docs[index] if index < len(docs) else "",
                "chapter_id": meta.get("chapter_id", ""),
                "chapter_title": meta.get("chapter_title", ""),
                "heading_path": meta.get("heading_path", ""),
            })
        return output

    def collection_exists(self, book_id: str) -> bool:
        try:
            self._client.get_collection(self._collection_name(book_id))
            return True
        except Exception:
            return False
