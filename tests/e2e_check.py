"""
FAZA 14 - Test E2E. Uruchamia pytania przez pelny pipeline (retrieval -> LLM),
weryfikuje structured output i FLAGUJE halucynacje citation: kazdy numer
artykulu / rzymski zalacznik w legal_basis, ktorego NIE MA w indeksie.
Uruchom:  python tests/e2e_check.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from rag import answer_question  # noqa: E402

QUESTIONS = [
    "Czy tacka PP do dania gotowego bedzie mogla byc uzywana po 2030 roku?",
    "Czy opakowania kompostowalne sa wyjatkiem od wymogow recyklingu?",
    "Jak wykazac zgodnosc opakowania z wymogami recyklingu?",
    "Co z selektywna zbiorka odpadow opakowaniowych?",
    "Jakie klasy mozliwosci recyklingu beda obowiazywac i od kiedy?",
]

ART_RE = re.compile(r"art\.?\s*(\d+)", re.IGNORECASE)
ANX_RE = re.compile(r"za[lł][aą]cznik\w*\s+([IVXLCDM]+)", re.IGNORECASE)


def main():
    chunks = json.load(open(ROOT / "index" / "chunks.json", encoding="utf-8"))
    valid_art = {c["article"] for c in chunks if c["article"]}
    valid_anx = {c["annex"] for c in chunks if c["annex"]}

    results, any_halluc = [], False
    for q in QUESTIONS:
        res = answer_question(q)
        a = res["answer"]
        cited = " | ".join(a.legal_basis + a.sources)
        arts = set(ART_RE.findall(cited))
        anxs = {x.upper() for x in ANX_RE.findall(cited)}
        bad_art = sorted(arts - valid_art)
        bad_anx = sorted(anxs - valid_anx)
        halluc = bool(bad_art or bad_anx)
        any_halluc = any_halluc or halluc
        results.append({
            "q": q, "insufficient": a.insufficient_context, "confidence": a.confidence,
            "legal_basis": a.legal_basis, "halluc_art": bad_art, "halluc_anx": bad_anx,
        })
        print(f"\nQ: {q}")
        print(f"  insufficient={a.insufficient_context} confidence={a.confidence}")
        print(f"  legal_basis={a.legal_basis}")
        print(f"  HALLUCINATED citations: {'NONE' if not halluc else str(bad_art)+str(bad_anx)}")

    ok = not any_halluc
    print(f"\n=== E2E: {len(QUESTIONS)} pytan | halucynacje citation: "
          f"{'BRAK' if ok else 'WYKRYTE'} | RESULT: {'PASS' if ok else 'FAIL'} ===")
    json.dump(results, open(ROOT / "index" / "e2e_results.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
