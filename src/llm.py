"""
FAZY 11 + 12 - Warstwa LLM (Anthropic) + guardrails.

Abstrakcja: generate_answer(question, sources) -> RagAnswer.
Structured output walidowany Pydantikiem (client.messages.parse). System prompt
wymusza odpowiadanie WYLACZNIE z retrieved context, oddzielanie motywow od norm,
zachowanie warunkowych dat i ustawianie insufficient_context przy braku podstawy.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from config import ANTHROPIC_MODEL


# ------------------------------------------------------------- schemat (sekcja 12)
class RagAnswer(BaseModel):
    answer: str
    legal_basis: list[str] = Field(default_factory=list)
    reasoning: str = ""
    quotes: list[str] = Field(default_factory=list)
    complementary_provisions: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    deadlines: list[str] = Field(default_factory=list)
    practical_implications: str = ""
    sources: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "low"
    insufficient_context: bool = False


SYSTEM_PROMPT = """\
Jestes asystentem prawnym analizujacym Rozporzadzenie (UE) 2025/40 (PPWR).
Odpowiadasz pracownikowi dzialu opakowan firmy spozywczej. Jezyk: polski.

ZASADY BEZWZGLEDNE (naruszenie = blad krytyczny):
1. Odpowiadaj WYLACZNIE na podstawie fragmentow w sekcji KONTEKST. Nie uzywaj
   wiedzy wlasnej jako niewidocznej podstawy prawnej.
2. Kazda teza prawna musi miec zrodlo wskazujace DOKLADNA jednostke (np.
   "Art. 6 ust. 3", "Zalacznik II tabela 3"). Nie wymyslaj artykulow, ustepow,
   punktow, liter, zalacznikow, wyjatkow ani terminow, ktorych nie ma w kontekscie.
3. Oddzielaj MOTYWY (recital) od NORM. Motyw nie moze byc przedstawiony jako
   samodzielna podstawa obowiazku prawnego - sluzy tylko interpretacji.
4. Zawsze sprawdzaj i wskazuj: wyjatki, odstepstwa, przepisy przejsciowe.
5. Zachowuj WARUNKOWE DATY doslownie. Jesli przepis mowi "od 1 stycznia 2030 r.
   lub X miesiecy od wejscia w zycie aktu, w zaleznosci od tego ktora data jest
   pozniejsza" - NIE upraszczaj do samego roku.
6. Jesli PPWR zapowiada przyszly akt delegowany lub wykonawczy, ktorego tresci
   nie ma w kontekscie - powiedz to wprost i NIE zgaduj jego tresci. To NIE jest
   powod do wylaczenia odpowiedzi: przedstaw RAMY (obowiazek, warunkowe daty,
   kategorie, zalaczniki, przepisy komplementarne), a szczegoly odloz jasno do
   przyszlego aktu.
7. Oddzielaj literalna podstawe prawna (pole reasoning/legal_basis) od
   praktycznego znaczenia dla dzialu opakowan (pole practical_implications).
8. FAIL-SAFE - kiedy insufficient_context=true: TYLKO gdy w kontekscie NIE MA
   ZADNEJ istotnej podstawy normatywnej dla tematu pytania (np. pytanie spoza
   zakresu PPWR - podatki, prawo pracy), albo gdy zrodla sa sprzeczne. Sam fakt,
   ze pelna/ostateczna odpowiedz zalezy od przyszlego aktu delegowanego NIE
   uzasadnia insufficient_context=true - jesli istnieje podstawa ramowa w
   kontekscie, ODPOWIEDZ na jej podstawie (confidence medium), wskazujac co
   pozostaje do doprecyzowania. Brak odpowiedzi jest lepszy niz odpowiedz
   falszywa, ale odpowiedz ramowa z zastrzezeniem jest lepsza niz milczenie, gdy
   podstawa ramowa istnieje.

FORMAT: wypelnij pola schematu. legal_basis i sources = dokladne jednostki
prawne (np. "Art. 6 ust. 3", "Zalacznik VII"). quotes = doslowne, krotkie cytaty
z kontekstu. Gdy insufficient_context=true, w answer napisz krotko czego brakuje.
"""


# Limit dlugosci pojedynczego fragmentu w kontekscie (oszczednosc tokenow wejscia).
# Najdluzsze jednostki (definicje art. 3, sekcje zalacznikow) sa przycinane.
MAX_SRC_CHARS = 2500


def _format_sources(sources: list[dict]) -> str:
    """Buduje blok KONTEKST z provenance kazdego fragmentu."""
    lines = []
    for i, c in enumerate(sources, 1):
        func = c.get("legal_function")
        tag = {"normative": "NORMA", "annex": "ZALACZNIK",
               "recital": "MOTYW (nie jest samodzielna podstawa)"}.get(func, func or "?")
        cit = c.get("citation") or c.get("stable_chunk_id")
        text = c.get("text", "") or ""
        if len(text) > MAX_SRC_CHARS:
            text = text[:MAX_SRC_CHARS] + " […fragment przycięty]"
        lines.append(f"[{i}] ({tag}) {cit}  <id:{c.get('stable_chunk_id')}>\n{text}")
    return "\n\n".join(lines)


def generate_answer(question: str, sources: list[dict], model: str | None = None) -> RagAnswer:
    """Zwraca RagAnswer (structured) na podstawie pytania i retrieved sources."""
    import anthropic
    from config import ANTHROPIC_API_KEY

    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "Brak ANTHROPIC_API_KEY. Ustaw sekret w .env (patrz .env.example) "
            "i pamietaj o limicie zuzycia w Anthropic Console."
        )
    if not sources:
        return RagAnswer(
            answer="Nie znalazlem wystarczajacej podstawy w dostepnych zrodlach.",
            confidence="low", insufficient_context=True,
        )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    user = (
        f"PYTANIE:\n{question}\n\n"
        f"KONTEKST (jedyne dozwolone zrodla):\n{_format_sources(sources)}"
    )
    # Koszt: thinking wylaczone (zadanie = wyciaganie z podanego tekstu, nie
    # gleboka analiza) + niski max_tokens. To glowne oszczednosci na wyjsciu.
    resp = client.messages.parse(
        model=model or ANTHROPIC_MODEL,
        max_tokens=8000,  # zlozone pytania daja dlugi structured output; 4000 urywalo JSON
        thinking={"type": "disabled"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user}],
        output_format=RagAnswer,
    )
    return resp.parsed_output


if __name__ == "__main__":
    import sys

    sys.path.insert(0, ".")
    from src.retrieval import expand_context

    q = " ".join(sys.argv[1:]) or "Co mowi art. 6 ust. 3 o klasach recyklingu?"
    ctx = expand_context(q)["context"]
    ans = generate_answer(q, ctx)
    print(ans.model_dump_json(indent=2))
