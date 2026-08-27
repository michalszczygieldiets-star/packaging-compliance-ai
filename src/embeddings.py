"""
FAZA 7 - Embeddings i indeks wektorowy.

Abstrakcja nad providerem embeddingow (Voyage / lokalny) i baza wektorowa
(FAISS lub Chroma). Deterministyczny wymiar. Klucz API tylko z sekretu.
UWAGA (Python 3.14): jesli brak wheeli FAISS/torch - plan B to Chroma +
embeddingi przez API (Voyage).
"""
from __future__ import annotations


def embed_texts(texts):
    """Zwraca wektory dla listy tekstow (batch)."""
    raise NotImplementedError("Do zbudowania w Fazie 7.")


def build_index(chunks):
    """Buduje i zapisuje indeks wektorowy z chunkow."""
    raise NotImplementedError("Do zbudowania w Fazie 7.")


def load_index():
    """Laduje zapisany indeks wektorowy."""
    raise NotImplementedError("Do zbudowania w Fazie 7.")
