"""
FAZA 7 - Embeddings i indeks wektorowy.

Provider lokalny (fastembed / ONNX, keyless) z abstrakcja umozliwiajaca
pozniejszy swap na Voyage. Indeks: FAISS IndexFlatIP na znormalizowanych
wektorach = cosine similarity. Kazdy passage dziedziczy tytul artykulu i
cytat (kontekst dla embeddingu). Model e5 wymaga prefiksow query:/passage:.
"""
from __future__ import annotations

import json

import numpy as np

from config import (
    EMB_META_PATH,
    EMBEDDING_PROVIDER,
    ID_MAP_PATH,
    LOCAL_EMBEDDING_MODEL,
    VECTOR_FAISS_PATH,
)

_model = None
_is_e5 = "e5" in LOCAL_EMBEDDING_MODEL.lower()


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        _model = TextEmbedding(model_name=LOCAL_EMBEDDING_MODEL)
    return _model


def passage_text(chunk: dict) -> str:
    """Tekst do embeddingu = kontekst prawny (dziedziczony) + tresc."""
    ctx = []
    if chunk.get("article"):
        ctx.append(f"Artykul {chunk['article']}")
    if chunk.get("article_title"):
        ctx.append(chunk["article_title"])
    if chunk.get("annex"):
        ctx.append(f"Zalacznik {chunk['annex']}")
    header = " - ".join(ctx)
    body = chunk["text"]
    return f"{header}. {body}" if header else body


def _embed(texts: list[str], kind: str) -> np.ndarray:
    if EMBEDDING_PROVIDER != "local":
        raise NotImplementedError("Tylko provider 'local' na MVP (swap Voyage: TODO).")
    if _is_e5:
        prefix = "query: " if kind == "query" else "passage: "
        texts = [prefix + t for t in texts]
    model = _get_model()
    vecs = np.array(list(model.embed(texts)), dtype="float32")
    # normalizacja L2 -> inner product = cosine
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


def embed_passages(chunks: list[dict]) -> np.ndarray:
    return _embed([passage_text(c) for c in chunks], kind="passage")


def embed_query(query: str) -> np.ndarray:
    return _embed([query], kind="query")[0]


def build_index(chunks: list[dict]) -> dict:
    """Buduje i zapisuje FAISS + mape ID. Zwraca meta."""
    import faiss

    vecs = embed_passages(chunks)
    dim = int(vecs.shape[1])
    index = faiss.IndexFlatIP(dim)
    index.add(vecs)
    faiss.write_index(index, str(VECTOR_FAISS_PATH))

    id_map = [c["stable_chunk_id"] for c in chunks]
    json.dump(id_map, open(ID_MAP_PATH, "w", encoding="utf-8"), ensure_ascii=False)
    meta = {"model": LOCAL_EMBEDDING_MODEL, "dim": dim, "count": len(chunks),
            "provider": EMBEDDING_PROVIDER}
    json.dump(meta, open(EMB_META_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return meta


def load_index():
    """Zwraca (faiss_index, id_map, meta)."""
    import faiss

    index = faiss.read_index(str(VECTOR_FAISS_PATH))
    id_map = json.load(open(ID_MAP_PATH, encoding="utf-8"))
    meta = json.load(open(EMB_META_PATH, encoding="utf-8"))
    return index, id_map, meta


def search(query: str, top_k: int = 8) -> list[tuple[str, float]]:
    """Zwraca [(stable_chunk_id, score)] posortowane malejaco."""
    index, id_map, _ = load_index()
    q = embed_query(query).reshape(1, -1)
    scores, idxs = index.search(q, top_k)
    return [(id_map[i], float(s)) for i, s in zip(idxs[0], scores[0]) if i >= 0]
