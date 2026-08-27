"""
FAZY 8 + 10 - Retrieval (exact + semantic) + context expansion.

Exact citation lookup (Faza 8): query parser (regex) + DETERMINISTYCZNY lookup
po metadanych. Nie zgaduje numeru, ktorego uzytkownik nie podal. Obsluguje
warianty pisowni, brak polskich znakow i numeracje rzymska.

Semantic search (Faza 8): FAISS vector search.
Ranking: gdy pytanie zawiera jawny cytat -> exact match ma pierwszenstwo.
Context expansion (Faza 10): dokladanie ustepow tego samego artykulu,
references, definicji, zalacznikow, wyjatkow - w jawnym budzecie.
"""
from __future__ import annotations

import json
import re
import unicodedata

from config import CHUNKS_PATH, CONTEXT_BUDGET_CHUNKS, TOP_K

# ------------------------------------------------------------------ dane
_CHUNKS = None
_BY_ID = None
_BM25 = None
_BM25_IDS = None


def _load_chunks():
    global _CHUNKS, _BY_ID
    if _CHUNKS is None:
        _CHUNKS = json.load(open(CHUNKS_PATH, encoding="utf-8"))
        _BY_ID = {c["stable_chunk_id"]: c for c in _CHUNKS}
    return _CHUNKS, _BY_ID


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", _fold(text))


def _get_bm25():
    """Leniwie buduje BM25 nad korpusem (tytul artykulu + tresc)."""
    global _BM25, _BM25_IDS
    if _BM25 is None:
        from rank_bm25 import BM25Okapi

        chunks, _ = _load_chunks()
        corpus = [_tokenize(f"{c.get('article_title') or ''} {c['text']}") for c in chunks]
        _BM25 = BM25Okapi(corpus)
        _BM25_IDS = [c["stable_chunk_id"] for c in chunks]
    return _BM25, _BM25_IDS


# ------------------------------------------------------------- normalizacja
def _fold(s: str) -> str:
    """Lower + usuniecie polskich znakow (do dopasowania wariantow pisowni)."""
    s = s.replace("ł", "l").replace("Ł", "L")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


_ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}


def _roman_to_int(s: str) -> int | None:
    s = s.lower()
    if not s or any(ch not in _ROMAN for ch in s):
        return None
    total = 0
    for i, ch in enumerate(s):
        v = _ROMAN[ch]
        nxt = _ROMAN[s[i + 1]] if i + 1 < len(s) else 0
        total += -v if v < nxt else v
    return total


def _int_to_roman(n: int) -> str:
    table = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"),
             (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"),
             (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for val, sym in table:
        while n >= val:
            out += sym
            n -= val
    return out


# ------------------------------------------------------------- parse citation
ART_RE = re.compile(r"\bart\.?\s*(\d+)")
UST_RE = re.compile(r"\bust\.?\s*(\d+)")
PKT_RE = re.compile(r"\bpkt\.?\s*(\d+)")
LIT_RE = re.compile(r"\blit\.?\s*([a-z])\b")
ANX_RE = re.compile(r"\bza(?:l|ł)acznik\w*\s+([ivxlcdm]+|\d+)")
CPT_RE = re.compile(r"\brozdzia(?:l|ł)\w*\s+([ivxlcdm]+|\d+)")


def parse_citation(query: str) -> dict | None:
    """Wykrywa jawne odeslanie. Zwraca dict z obecnymi polami lub None.
    NIE zgaduje numerow, ktorych uzytkownik nie podal."""
    q = _fold(query)
    cit = {}

    m = ART_RE.search(q)
    if m:
        cit["article"] = m.group(1)
        if (u := UST_RE.search(q)):
            cit["paragraph"] = u.group(1)
        if (p := PKT_RE.search(q)):
            cit["point"] = p.group(1)
        if (l := LIT_RE.search(q)):
            cit["letter"] = l.group(1)

    m = ANX_RE.search(q)
    if m:
        raw = m.group(1)
        num = _roman_to_int(raw) if not raw.isdigit() else int(raw)
        if num:
            cit["annex"] = _int_to_roman(num)

    m = CPT_RE.search(q)
    if m:
        raw = m.group(1)
        num = _roman_to_int(raw) if not raw.isdigit() else int(raw)
        if num:
            cit["chapter"] = _int_to_roman(num)

    return cit or None


# ------------------------------------------------------------- exact lookup
def exact_lookup(citation: dict) -> list[dict]:
    """Deterministyczny lookup po metadanych. Zwraca chunki w kolejnosci dok."""
    chunks, _ = _load_chunks()
    if not citation:
        return []

    def matches(c) -> bool:
        if "annex" in citation:
            if c.get("annex") != citation["annex"]:
                return False
        if "article" in citation:
            if c.get("article") != citation["article"]:
                return False
            if "paragraph" in citation and c.get("paragraph") != citation["paragraph"]:
                return False
            if "letter" in citation and citation["letter"] and c.get("letter") != citation["letter"]:
                return False
            if "point" in citation and citation["point"] and c.get("point") != citation["point"]:
                return False
        if "chapter" in citation and "article" not in citation and "annex" not in citation:
            if c.get("chapter") != citation["chapter"]:
                return False
        return True

    # zaweznie: jesli podano ust/lit/pkt, a nie ma dokladnego trafienia
    # (bo ustep zostal rozbity na punkty) -> zwroc wszystkie chunki tego ustepu
    res = [c for c in chunks if matches(c)]
    if not res and "paragraph" in citation:
        loose = dict(citation)
        loose.pop("letter", None)
        loose.pop("point", None)
        res = [c for c in chunks
               if c.get("article") == loose.get("article")
               and c.get("paragraph") == loose.get("paragraph")]
    return res


# ------------------------------------------------------------- semantic
def semantic_search(query: str, top_k: int = TOP_K) -> list[tuple[dict, float]]:
    from src.embeddings import search

    _, by_id = _load_chunks()
    hits = search(query, top_k=top_k)
    return [(by_id[cid], score) for cid, score in hits if cid in by_id]


def lexical_search(query: str, top_k: int = TOP_K) -> list[tuple[dict, float]]:
    """BM25 nad korpusem - lapie pytania sterowane slowem kluczowym."""
    bm, ids = _get_bm25()
    _, by_id = _load_chunks()
    scores = bm.get_scores(_tokenize(query))
    order = sorted(range(len(ids)), key=lambda i: -scores[i])[:top_k]
    return [(by_id[ids[i]], float(scores[i])) for i in order]


def hybrid_search(query: str, pool: int = 30) -> list[tuple[dict, float]]:
    """Fuzja wektorowa + BM25 metoda Reciprocal Rank Fusion (RRF).
    Semantyka lapie parafrazy, BM25 lapie terminy - razem odporniejsze."""
    _, by_id = _load_chunks()
    vec = [cid for cid, _ in
           [(c["stable_chunk_id"], s) for c, s in semantic_search(query, top_k=pool)]]
    lex = [c["stable_chunk_id"] for c, _ in lexical_search(query, top_k=pool)]
    vr = {cid: i for i, cid in enumerate(vec)}
    lr = {cid: i for i, cid in enumerate(lex)}
    K = 60
    fused = {}
    for cid in set(vr) | set(lr):
        fused[cid] = 1.0 / (K + vr.get(cid, 9999)) + 1.0 / (K + lr.get(cid, 9999))
    ranked = sorted(fused, key=lambda c: -fused[c])
    return [(by_id[cid], fused[cid]) for cid in ranked]


# ------------------------------------------------------------- combined (Faza 8)
def retrieve(query: str, top_k: int = TOP_K) -> dict:
    """Exact + hybrid (semantic+BM25). Ranking: exact ma pierwszenstwo przy
    jawnym cytacie. Zwraca {citation, exact, semantic, ranked}."""
    citation = parse_citation(query)
    exact = exact_lookup(citation) if citation else []
    fused = hybrid_search(query)

    ranked, seen = [], set()
    for c in exact:  # exact najpierw (jawny cytat)
        if c["stable_chunk_id"] not in seen:
            ranked.append(c)
            seen.add(c["stable_chunk_id"])
    for c, _ in fused:
        if c["stable_chunk_id"] not in seen:
            ranked.append(c)
            seen.add(c["stable_chunk_id"])

    return {"citation": citation, "exact": exact, "semantic": fused[:top_k],
            "ranked": ranked[:CONTEXT_BUDGET_CHUNKS]}


# ------------------------------------------------------------- context expansion (Faza 10)
_PRIORITY = {"normative": 0, "annex": 1, "recital": 2}


def _resolve_target(target: str) -> list[dict]:
    """Zamienia ID-cel odeslania na istniejace chunki (z budzetowaniem)."""
    chunks, by_id = _load_chunks()
    if target in by_id:
        return [by_id[target]]
    # ustep rozbity na punkty: ART{a}_P{p} -> wszystkie punkty tego ustepu
    m = re.match(r"(.+)_ART(\d+)_P(\d+)$", target)
    if m:
        art, p = m.group(2), m.group(3)
        hits = [c for c in chunks if c.get("article") == art and c.get("paragraph") == p]
        if hits:
            return hits
    # caly artykul ART{a} -> reprezentatywnie ust. 1 (lub pierwszy chunk)
    m = re.match(r"(.+)_ART(\d+)$", target)
    if m:
        art = m.group(2)
        hits = [c for c in chunks if c.get("article") == art]
        return hits[:1]
    # zalacznik ANX_{roman} -> preferuj sekcje z tabela, max 2
    m = re.match(r"(.+)_ANX_([IVXLCDM]+)$", target)
    if m:
        roman = m.group(2)
        secs = [c for c in chunks if c.get("annex") == roman]
        tabled = [c for c in secs if c.get("table")]
        pick = (tabled or secs)[:2]
        return pick
    return []


def expand_context(query: str, budget: int = 14, primary_k: int = 5,
                   ref_cap: int = 8) -> dict:
    """Faza 10: kolejnosc gwarantuje przetrwanie komplementarnych jednostek.
    context = [exact] + [czolowe seedy] + [ICH bezposrednie references] +
    [reszta fuzji], dedup, w jawnym budzecie. Dzieki temu np. Zalacznik II
    i art. 48 (references art. 6) nie sa wypychane przez luzne chunki fuzji.
    Zwraca {citation, seeds, context, added_refs}."""
    r = retrieve(query)
    exact = r["exact"]
    fused = r["ranked"]

    seen = set()
    order = []

    def take(c):
        if c["stable_chunk_id"] not in seen:
            seen.add(c["stable_chunk_id"])
            order.append(c)
            return True
        return False

    # 1) jednostki z jawnego cytatu (najwyzszy priorytet)
    for c in exact:
        take(c)
    # 2) czolowe seedy z fuzji
    primary = [c for c in fused if c["stable_chunk_id"] not in seen][:primary_k]
    for c in primary:
        take(c)
    # 3) bezposrednie references jednostek z (1)+(2) - PRZED reszta fuzji
    added_refs, used = [], 0
    for c in list(exact) + primary:
        for ref in c.get("references", []):
            if used >= ref_cap:
                break
            for tgt in _resolve_target(ref["target"]):
                if take(tgt):
                    added_refs.append(tgt["stable_chunk_id"])
                    used += 1
    # 4) reszta fuzji do wypelnienia budzetu
    for c in fused:
        if len(order) >= budget:
            break
        take(c)

    context = order[:budget]
    return {"citation": r["citation"], "seeds": fused,
            "context": context, "added_refs": added_refs}


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "Co mowi art. 6 ust. 3?"
    print("QUERY:", q)
    print("CITATION:", parse_citation(q))
    e = expand_context(q)
    print(f"\n--- CONTEXT ({len(e['context'])} chunkow, added_refs={len(e['added_refs'])}) ---")
    for c in e["context"]:
        print(f"  [{c.get('legal_function','?'):9}] {c['stable_chunk_id']:26} | {c['citation']}")
