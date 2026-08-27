"""
FAZA 5 - Legal-aware chunking + metadata.

Granice jednostek prawnych maja pierwszenstwo przed rozmiarem tokenowym.
oversized_unit_rule (kolejnosc): artykul -> ustep (struktura) -> punkt/litera
-> techniczny split tokenowy (ostatecznosc). Kazdy chunk niesie pelna sciezke
prawna, tytul artykulu (dziedziczony) i stabilny, deterministyczny ID.

Schemat ID:
  ustep:      EU2025_40_ART6_P3
  punkt:      EU2025_40_ART6_P4_B      (litera) / EU2025_40_ART3_P1_38 (numer)
  split tech: EU2025_40_ART3_P1_38_PART1
  zalacznik:  EU2025_40_ANX_II_S3
  motyw:      EU2025_40_REC_15
"""
from __future__ import annotations

import re

from config import (
    DOCUMENT_ID,
    DOCUMENT_TITLE,
    HARD_SPLIT_TOKENS,
    MAX_CHUNK_TOKENS,
    STABLE_ID_PREFIX,
)
from src.parser import parse_source

SOURCE_TYPE = "EU LAW"
TABELA_RE = re.compile(r"tabela\s+(\d+)", re.IGNORECASE)


def approx_tokens(text: str) -> int:
    """Zgrubny licznik tokenow dla PL (~4 znaki/token)."""
    return max(1, len(text or "") // 4)


def _technical_split(text: str, base_id: str, limit: int) -> list[tuple[str, str]]:
    """Ostatecznosc: dziel po zdaniach do <= limit. Zwraca [(suffix_id, text)]."""
    sentences = re.split(r"(?<=[.;:])\s+", text)
    parts, cur = [], ""
    for s in sentences:
        if cur and approx_tokens(cur + " " + s) > limit:
            parts.append(cur.strip())
            cur = s
        else:
            cur = (cur + " " + s).strip()
    if cur.strip():
        parts.append(cur.strip())
    if len(parts) <= 1:
        return [(base_id, text)]
    return [(f"{base_id}_PART{i+1}", p) for i, p in enumerate(parts)]


def _mk(**kw) -> dict:
    """Buduje rekord chunku z pelnym schematem metadanych (sekcja 6)."""
    base = {
        "document_id": DOCUMENT_ID,
        "document_title": DOCUMENT_TITLE,
        "source_type": SOURCE_TYPE,
        "section_type": None,
        "legal_function": None,
        "chapter": None,
        "article": None,
        "article_title": None,
        "paragraph": None,
        "point": None,
        "letter": None,
        "annex": None,
        "table": None,
        "text": "",
        "citation": None,
        "source_file_or_url": "data/raw/ppwr_pl.html",
        "stable_chunk_id": None,
        "parent_id": None,
        "references": [],
    }
    base.update(kw)
    return base


def _point_fields(marker: str) -> dict:
    """Rozdziela marker na point (numer/rzymski) vs letter (a-z)."""
    if re.fullmatch(r"[a-z]{1,2}", marker):
        return {"point": None, "letter": marker}
    return {"point": marker, "letter": None}


def build_chunks(doc: dict) -> list[dict]:
    chunks: list[dict] = []

    # ---------- ARTYKULY / USTEPY / PUNKTY ----------
    for a in doc["articles"]:
        art = a["article"]
        art_id = f"{STABLE_ID_PREFIX}_ART{art}"
        title = a["article_title"]

        for p in a["paragraphs"]:
            pnum = p["paragraph"]
            pid = f"{art_id}_P{pnum}" if pnum else art_id
            citation_base = f"Art. {art}" + (f" ust. {pnum}" if pnum else "")
            common = dict(
                section_type="paragraph",
                legal_function="normative",
                chapter=a["chapter"],
                article=art,
                article_title=title,
                paragraph=pnum,
                parent_id=art_id,
            )
            text = p["text"]
            points = p.get("points") or []

            if approx_tokens(text) <= MAX_CHUNK_TOKENS or not points:
                # miesci sie -> jeden chunk; jesli i tak za duzy i brak punktow -> split tech.
                if approx_tokens(text) > HARD_SPLIT_TOKENS and not points:
                    for sid, frag in _technical_split(text, pid, MAX_CHUNK_TOKENS):
                        chunks.append(_mk(**common, text=frag, stable_chunk_id=sid,
                                          citation=citation_base))
                else:
                    chunks.append(_mk(**common, text=text, stable_chunk_id=pid,
                                      citation=citation_base))
            else:
                # oversized + ma punkty -> chunk na punkt (dziedziczy tytul/sciezke)
                for pt in points:
                    marker = pt["marker"]
                    sid = f"{pid}_{marker.upper()}"
                    pf = _point_fields(marker)
                    kind = "lit." if pf["letter"] else "pkt"
                    cit = f"{citation_base} {kind} {marker}"
                    ptext = pt["text"]
                    row = {**common, "section_type": "point", **pf}
                    if approx_tokens(ptext) > HARD_SPLIT_TOKENS:
                        for ssid, frag in _technical_split(ptext, sid, MAX_CHUNK_TOKENS):
                            chunks.append(_mk(**row, text=frag, stable_chunk_id=ssid, citation=cit))
                    else:
                        chunks.append(_mk(**row, text=ptext, stable_chunk_id=sid, citation=cit))

    # ---------- ZALACZNIKI ----------
    for anx in doc["annexes"]:
        roman = anx["annex"]
        anx_id = f"{STABLE_ID_PREFIX}_ANX_{roman}"
        common = dict(
            section_type="annex",
            legal_function="annex",
            annex=roman,
            article_title=anx["title"],
            parent_id=anx_id,
        )
        if approx_tokens(anx["text"]) <= MAX_CHUNK_TOKENS or not anx.get("sections"):
            chunks.append(_mk(**common, text=anx["text"], stable_chunk_id=anx_id,
                              citation=f"Zalacznik {roman}"))
            continue

        # scal naglowki-bez-tresci z nastepna sekcja (np. "Tabela 3" + podtytul)
        merged, pending = [], []
        for s in anx["sections"]:
            if not s["text"]:
                if s["heading"]:
                    pending.append(s["heading"])
                continue
            head = " - ".join([h for h in pending] + ([s["heading"]] if s["heading"] else []))
            merged.append({"heading": head or s["heading"], "text": s["text"]})
            pending = []

        for i, s in enumerate(merged, 1):
            sid = f"{anx_id}_S{i}"
            head = s["heading"] or ""
            tbl = TABELA_RE.search(head)
            cit = f"Zalacznik {roman}" + (f", {head}" if head else f", sekcja {i}")
            body = (head + "\n" + s["text"]).strip() if head else s["text"]
            if approx_tokens(body) > HARD_SPLIT_TOKENS:
                for ssid, frag in _technical_split(body, sid, MAX_CHUNK_TOKENS):
                    chunks.append(_mk(**common, text=frag, stable_chunk_id=ssid,
                                      table=(tbl.group(1) if tbl else None), citation=cit))
            else:
                chunks.append(_mk(**common, text=body, stable_chunk_id=sid,
                                  table=(tbl.group(1) if tbl else None), citation=cit))

    # ---------- MOTYWY (recitals) ----------
    for r in doc["recitals"]:
        rid = f"{STABLE_ID_PREFIX}_REC_{r['number']}"
        chunks.append(_mk(section_type="recital", legal_function="recital",
                          text=r["text"], stable_chunk_id=rid, parent_id=STABLE_ID_PREFIX,
                          citation=f"motyw {r['number']}"))

    return chunks


if __name__ == "__main__":
    doc = parse_source("data/raw/ppwr_pl.html")
    ch = build_chunks(doc)
    print("chunks:", len(ch))
