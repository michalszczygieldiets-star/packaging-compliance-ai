"""
FAZA 4 - Parser struktury prawnej (canonical source = Formex-HTML EUR-Lex).

Zamienia oficjalny HTML Rozp. (UE) 2025/40 na liste jednostek prawnych z
zachowaniem granic: chapter -> article -> paragraph oraz annex / recital.
NIE tnie po stalych rozmiarach tokenow - to robi dopiero chunker (Faza 5).

Struktura zrodla (ustalona empirycznie):
  <div class="eli-subdivision" id="art_6">        # artykul
     <p class="oj-ti-art">Artykul 6</p>           # numer
     <div class="eli-title" id="art_6.tit_1">..</div>   # tytul
     <div id="006.001">1.  ...</div>              # ustep (NNN.MMM)
     ...
  <div id="anx_II"> ... </div>                    # zalacznik (rzymski)
  <div id="rct_1"> ... </div>                     # motyw (recital)
"""
from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup

ART_ID_RE = re.compile(r"^art_(\d+)$")
PARA_ID_RE = re.compile(r"^\d{3}\.\d{3}$")
ANX_ID_RE = re.compile(r"^anx_([IVXLCDM]+)$")
RCT_ID_RE = re.compile(r"^rct_(\d+)$")
CPT_ID_RE = re.compile(r"^cpt_([IVXLCDM]+)$")
LEADING_NUM_RE = re.compile(r"^\s*(\d+)\.\s*")


def _norm(text: str) -> str:
    """Normalizuje biale znaki (w tym NBSP) bez zmiany tresci merytorycznej."""
    if not text:
        return ""
    text = text.replace("\xa0", " ").replace("­", "")
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    return text.strip()


def _chapter_of(node) -> str | None:
    """Numer rozdzialu (rzymski) z najblizszego przodka cpt_*, jesli jest."""
    for anc in node.parents:
        anc_id = anc.get("id") if hasattr(anc, "get") else None
        if anc_id:
            m = CPT_ID_RE.match(anc_id)
            if m:
                return m.group(1)
    return None


def _article_number(art_div) -> str | None:
    p = art_div.find("p", class_="oj-ti-art")
    if p:
        m = re.search(r"(\d+)", p.get_text(" ", strip=True))
        if m:
            return m.group(1)
    m = ART_ID_RE.match(art_div.get("id", ""))
    return m.group(1) if m else None


def _article_title(art_div) -> str | None:
    t = art_div.find(class_="eli-title")
    if t:
        return _norm(t.get_text(" ", strip=True))
    t = art_div.find("p", class_="oj-sti-art")
    return _norm(t.get_text(" ", strip=True)) if t else None


def parse_source(raw_path: str) -> dict:
    """Zwraca strukture: {articles: [...], annexes: [...], recitals: [...]}.

    article = {article, article_title, chapter, paragraphs:[{paragraph, text, html_id}]}
    annex   = {annex, title, text, n_tables}
    recital = {number, text}
    """
    html = open(raw_path, encoding="utf-8").read()
    soup = BeautifulSoup(html, "html.parser")

    articles = []
    for art_div in soup.find_all(id=ART_ID_RE):
        num = _article_number(art_div)
        title = _article_title(art_div)
        chapter = _chapter_of(art_div)

        paragraphs = []
        for para in art_div.find_all("div", id=PARA_ID_RE, recursive=False):
            raw = _norm(para.get_text(" ", strip=True))
            m = LEADING_NUM_RE.match(raw)
            p_num = m.group(1) if m else None
            paragraphs.append(
                {"paragraph": p_num, "text": raw, "html_id": para.get("id")}
            )

        # Artykul bez numerowanych ustepow -> jeden ustep = cale cialo (bez tytulu).
        if not paragraphs:
            body = art_div.get_text(" ", strip=True)
            if title:
                body = body.replace(title, "", 1)
            body = _norm(re.sub(r"^\s*Artyku[lł]\s*\d+\s*", "", body))
            if body:
                paragraphs.append({"paragraph": None, "text": body, "html_id": art_div.get("id")})

        articles.append(
            {
                "article": num,
                "article_title": title,
                "chapter": chapter,
                "paragraphs": paragraphs,
            }
        )

    annexes = []
    for anx in soup.find_all(id=ANX_ID_RE):
        roman = ANX_ID_RE.match(anx.get("id")).group(1)
        heading = anx.find(class_="eli-title") or anx.find("p", class_="oj-ti-annex")
        title = _norm(heading.get_text(" ", strip=True)) if heading else None
        annexes.append(
            {
                "annex": roman,
                "title": title,
                "text": _norm(anx.get_text(" ", strip=True)),
                "n_tables": len(anx.find_all("table")),
            }
        )

    recitals = []
    for rct in soup.find_all(id=RCT_ID_RE):
        recitals.append(
            {
                "number": RCT_ID_RE.match(rct.get("id")).group(1),
                "text": _norm(rct.get_text(" ", strip=True)),
            }
        )

    return {"articles": articles, "annexes": annexes, "recitals": recitals}


if __name__ == "__main__":
    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parent.parent
    doc = parse_source(str(ROOT / "data" / "raw" / "ppwr_pl.html"))
    print(
        f"articles={len(doc['articles'])} annexes={len(doc['annexes'])} "
        f"recitals={len(doc['recitals'])}"
    )
