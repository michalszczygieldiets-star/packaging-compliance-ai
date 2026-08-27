"""
FAZA 6 - Relacje prawne miedzy jednostkami.

Wykrywa JAWNE odeslania w tekscie i zapisuje je jako references[] w chunkach
oraz osobny relations.json. Bez Neo4j.

Kluczowe zasady:
- Odeslania ZEWNETRZNE (do innych aktow: "art. 1 dyrektywy 2001/83/WE",
  "zalaczniku XVII do rozporzadzenia (WE) nr 1907/2006") sa ODFILTROWANE -
  nie tworzymy z nich relacji wewnetrznych.
- Odeslania WZGLEDNE ("ust. 4 niniejszego artykulu", samo "ust. 5")
  rozwiazywane sa wzgledem artykulu, w ktorym wystepuja (etap ingestion).
- Emitujemy tylko krawedzie do jednostek, ktore ISTNIEJA w indeksie.

Typy: references_article, references_paragraph, references_annex,
references_table, exception_to.
"""
from __future__ import annotations

import re

from config import STABLE_ID_PREFIX as PFX

# --- wzorce ---
ART_RE = re.compile(r"art\.\s*(\d+)", re.IGNORECASE)
# "art. X ust. Y" oraz "ust. Y[ i Z]" (compound + relative)
ART_UST_RE = re.compile(r"art\.\s*(\d+)\s*ust\.\s*(\d+(?:\s*i\s*\d+)*)", re.IGNORECASE)
UST_RE = re.compile(r"ust\.\s*(\d+(?:\s*i\s*\d+)*)", re.IGNORECASE)
ANNEX_RE = re.compile(r"za[lł][aą]cznik\w*\s+([IVXLCDM]+)", re.IGNORECASE)
TABELA_RE = re.compile(r"tabel\w*\s+(\d+)", re.IGNORECASE)
DEROG_RE = re.compile(
    r"(?:na zasadzie|w\s+drodze)\s+odst[eę]pstwa\s+od\s+ust\.\s*(\d+(?:\s*i\s*\d+)*)",
    re.IGNORECASE,
)
# marker aktu zewnetrznego w oknie po odeslaniu
EXTERNAL_RE = re.compile(r"dyrektyw|\(WE\)|\(EWG\)|\d{3,4}/\d{1,4}|nr\s*\d", re.IGNORECASE)


def _nums(group: str) -> list[str]:
    """'1 i 5' -> ['1','5']"""
    return re.findall(r"\d+", group)


def _is_external(text: str, end_pos: int, window: int = 45) -> bool:
    return bool(EXTERNAL_RE.search(text[end_pos:end_pos + window]))


def build_valid_index(chunks: list[dict]) -> dict:
    """Zbiory istniejacych jednostek (logiczne ID) do walidacji krawedzi."""
    articles, paras, annexes = set(), set(), set()
    annex_tables = {}  # (roman, table) -> section chunk id
    for c in chunks:
        if c.get("article"):
            articles.add(c["article"])
            if c.get("paragraph"):
                paras.add(f"{PFX}_ART{c['article']}_P{c['paragraph']}")
        if c.get("annex"):
            annexes.add(c["annex"])
            if c.get("table"):
                annex_tables[(c["annex"], c["table"])] = c["stable_chunk_id"]
    return {"articles": articles, "paras": paras, "annexes": annexes,
            "annex_tables": annex_tables}


def extract_relations(chunks: list[dict]) -> list[dict]:
    """Uzupelnia chunk['references'] i zwraca plaska liste krawedzi."""
    idx = build_valid_index(chunks)
    edges = []

    for c in chunks:
        # relacje wykrywamy w tresci normatywnej i zalacznikach
        if c["section_type"] == "recital":
            continue
        text = c["text"]
        src = c["stable_chunk_id"]
        cur_art = c.get("article")
        refs = []

        def add(rtype, target, raw):
            if not any(r["type"] == rtype and r["target"] == target for r in refs):
                refs.append({"type": rtype, "target": target, "raw": raw})
                edges.append({"source": src, "type": rtype, "target": target})

        # 1) art. X ust. Y (compound) - i oznacz te spany jako "zuzyte"
        consumed = []
        for m in ART_UST_RE.finditer(text):
            if _is_external(text, m.end()):
                consumed.append((m.start(), m.end()))
                continue
            art = m.group(1)
            for y in _nums(m.group(2)):
                if f"{PFX}_ART{art}_P{y}" in idx["paras"]:
                    add("references_paragraph", f"{PFX}_ART{art}_P{y}", m.group(0))
                elif art in idx["articles"]:
                    add("references_article", f"{PFX}_ART{art}", m.group(0))
            consumed.append((m.start(), m.end()))

        def in_consumed(pos):
            return any(a <= pos < b for a, b in consumed)

        # 2) samodzielne art. N (wewnetrzne)
        for m in ART_RE.finditer(text):
            if in_consumed(m.start()) or _is_external(text, m.end()):
                continue
            art = m.group(1)
            if art in idx["articles"] and art != cur_art:
                add("references_article", f"{PFX}_ART{art}", m.group(0))

        # 3) samodzielne ust. Y -> WZGLEDNE do biezacego artykulu
        if cur_art:
            for m in UST_RE.finditer(text):
                if in_consumed(m.start()):
                    continue
                for y in _nums(m.group(1)):
                    tgt = f"{PFX}_ART{cur_art}_P{y}"
                    if tgt in idx["paras"]:
                        add("references_paragraph", tgt, m.group(0))

        # 4) zalaczniki (wewnetrzne)
        for m in ANNEX_RE.finditer(text):
            if _is_external(text, m.end()):
                continue
            roman = m.group(1).upper()
            if roman in idx["annexes"]:
                add("references_annex", f"{PFX}_ANX_{roman}", m.group(0))

        # 5) tabele -> mapuj na sekcje zalacznika II (glowny nosnik tabel art.6)
        for m in TABELA_RE.finditer(text):
            key = ("II", m.group(1))
            if key in idx["annex_tables"]:
                add("references_table", idx["annex_tables"][key], m.group(0))

        # 6) exception_to: "na zasadzie odstepstwa od ust. N"
        if cur_art:
            for m in DEROG_RE.finditer(text):
                for y in _nums(m.group(1)):
                    tgt = f"{PFX}_ART{cur_art}_P{y}"
                    if tgt in idx["paras"]:
                        add("exception_to", tgt, m.group(0))

        c["references"] = refs

    return edges


if __name__ == "__main__":
    import json
    chunks = json.load(open("index/chunks.json", encoding="utf-8"))
    edges = extract_relations(chunks)
    print("edges:", len(edges))
