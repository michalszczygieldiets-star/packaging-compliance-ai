"""
FAZA 5 - Legal-aware chunking + metadata.

Granice jednostek prawnych maja pierwszenstwo przed rozmiarem tokenowym.
oversized_unit_rule: artykul za duzy -> dziel po ustepach -> po punktach/literach
-> ostatecznie techniczny split tokenowy. Kazdy pod-chunk dziedziczy
parent_article_id, pelna sciezke prawna, tytul artykulu oraz stable_chunk_id
z deterministycznym sufiksem (np. EU2025_40_ART6_P3_PART1).
"""
from __future__ import annotations


def build_chunks(units):
    """Zwraca liste chunkow z pelnymi metadanymi i stabilnymi ID."""
    raise NotImplementedError("Do zbudowania w Fazie 5.")
