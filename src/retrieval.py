"""
FAZY 8 + 10 - Retrieval + context expansion.

1) Exact citation lookup (Faza 8): query parser (regex) + deterministyczny
   lookup po metadanych. Warianty: 'art. 6', 'art 6', 'art. 6 ust. 3 lit. b',
   'zalacznik II', numeracja rzymska. Normalizuje wielkosc liter i brak
   polskich znakow, ale NIE zgaduje numeru, ktorego uzytkownik nie podal.
2) Semantic search (Faza 8): vector search po tresci.
3) Ranking: exact match ma pierwszenstwo, gdy pytanie zawiera jawne citation.
4) Context expansion (Faza 10): dokladane ustepy tego samego artykulu,
   references, definicje, zalaczniki, wyjatki, terminy - w jawnym budzecie.
"""
from __future__ import annotations


def parse_citation(query):
    """Wykrywa jawne odeslanie w pytaniu (art./ust./pkt/lit./zalacznik)."""
    raise NotImplementedError("Do zbudowania w Fazie 8.")


def exact_lookup(citation):
    """Deterministyczny lookup jednostki prawnej po metadanych."""
    raise NotImplementedError("Do zbudowania w Fazie 8.")


def semantic_search(query, top_k):
    """Wyszukiwanie semantyczne (vector search)."""
    raise NotImplementedError("Do zbudowania w Fazie 8.")


def retrieve(query):
    """Pelny pipeline: citation -> exact/semantic -> context expansion."""
    raise NotImplementedError("Do zbudowania w Fazach 8/10.")
