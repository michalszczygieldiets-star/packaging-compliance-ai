"""
FAZA 6 - Relacje prawne miedzy jednostkami.

Wykrywa jawne odeslania: references_article, references_paragraph,
references_annex, exception_to, depends_on, implemented_by.
Odeslania wzgledne ("ust. 4 niniejszego artykulu") rozwiazywane sa na etapie
ingestion wzgledem biezacego artykulu - nie na etapie zapytania uzytkownika.
Bez Neo4j - relacje zapisywane w JSON/metadanych.
"""
from __future__ import annotations


def extract_relations(chunks):
    """Zwraca graf odeslan (lista krawedzi) miedzy stable_chunk_id."""
    raise NotImplementedError("Do zbudowania w Fazie 6.")
