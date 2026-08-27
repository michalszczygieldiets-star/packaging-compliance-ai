"""
FAZA 4 - Parser struktury prawnej.

Zamienia canonical source (HTML/XML/PDF) na liste jednostek prawnych:
document -> chapter -> article -> paragraph -> point -> letter -> annex -> table.
Zachowuje granice jednostek; NIE tnie po stalych rozmiarach tokenow.

Sanity checks (BLOCKING, Faza 17): istnieje art. 1, art. 6, art. 65,
zalacznik II; art. 6 ma poprawny tytul i wykryte ustepy.
"""
from __future__ import annotations


def parse_source(raw_path):
    """Zwraca liste surowych jednostek prawnych z canonical source."""
    raise NotImplementedError("Do zbudowania w Fazie 4.")
