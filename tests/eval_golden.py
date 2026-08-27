"""
FAZA 9 - Ewaluacja golden dataset.

Metryka glowna: czy retrieval znalazl oczekiwana podstawe prawna (glowny
expected_article w zwroconym zbiorze). Poboczne: wymagany annex znaleziony;
exact lookup zwraca poprawna jednostke.

Regula diagnozy: gdy expected_article NIE trafia, sprawdz czy jednostka w ogole
istnieje w indeksie -> odroznij blad PARSERA od bledu RETRIEVALU.

Uruchom:  python tests/eval_golden.py
Wynik zapisywany do index/eval_results.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.retrieval import exact_lookup, parse_citation, retrieve  # noqa: E402

TOP_K = 10


def _articles_in_index(chunks):
    return {c["article"] for c in chunks if c["article"]}


def main() -> int:
    golden = json.load(open(ROOT / "tests" / "golden_questions.json", encoding="utf-8"))
    chunks = json.load(open(ROOT / "index" / "chunks.json", encoding="utf-8"))
    idx_articles = _articles_in_index(chunks)

    rows, main_pass, annex_ok, annex_total, exact_ok, exact_total = [], 0, 0, 0, 0, 0

    for g in golden:
        q = g["question"]
        r = retrieve(q, top_k=TOP_K)
        got_arts = [c["article"] for c in r["ranked"] if c["article"]]
        got_annex = {c["annex"] for c in r["ranked"] if c["annex"]}

        exp_main = g["expected_articles"][0] if g["expected_articles"] else None
        found_main = exp_main in got_arts if exp_main else True
        cover = [a for a in g["expected_articles"] if a in got_arts]

        # diagnoza parser vs retrieval
        diag = ""
        if exp_main and not found_main:
            diag = ("PARSER?" if exp_main not in idx_articles else "RETRIEVAL")

        # annex (poboczne)
        a_ok = True
        for anx in g["expected_annexes"]:
            annex_total += 1
            if anx in got_annex:
                annex_ok += 1
            else:
                a_ok = False

        # exact (poboczne) - tylko dla trybu exact
        ex_ok = None
        if g["retrieval_mode"] == "exact":
            exact_total += 1
            cit = parse_citation(q)
            ex = exact_lookup(cit) if cit else []
            ex_arts = {c["article"] for c in ex if c["article"]}
            ex_anx = {c["annex"] for c in ex if c["annex"]}
            ex_ok = (exp_main in ex_arts) if exp_main else bool(ex_anx & set(g["expected_annexes"]))
            if not g["expected_articles"]:
                ex_ok = bool(ex_anx & set(g["expected_annexes"]))
            if ex_ok:
                exact_ok += 1

        main_pass += int(found_main)
        rows.append({
            "id": g["id"], "q": q, "mode": g["retrieval_mode"],
            "expected": g["expected_articles"], "expected_annex": g["expected_annexes"],
            "main_found": found_main, "coverage": cover,
            "annex_ok": a_ok if g["expected_annexes"] else None,
            "exact_ok": ex_ok, "diag": diag,
            "top_articles": got_arts[:6],
        })

    n = len(golden)
    print(f"=== GOLDEN EVAL ({n} pytan, top_k={TOP_K}) ===")
    for r in rows:
        flag = "PASS" if r["main_found"] else f"FAIL[{r['diag']}]"
        extra = ""
        if r["annex_ok"] is not None:
            extra += f" annex={'OK' if r['annex_ok'] else 'MISS'}"
        if r["exact_ok"] is not None:
            extra += f" exact={'OK' if r['exact_ok'] else 'MISS'}"
        print(f"  #{r['id']:>2} [{r['mode']:8}] {flag:16} exp={r['expected']}{extra} "
              f"top={r['top_articles']}")

    print(f"\nMAIN BASIS: {main_pass}/{n} ({100*main_pass//n}%)")
    if annex_total:
        print(f"ANNEX (poboczne): {annex_ok}/{annex_total}")
    if exact_total:
        print(f"EXACT (poboczne): {exact_ok}/{exact_total}")

    json.dump(rows, open(ROOT / "index" / "eval_results.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # krytyczne pytania art. 6 musza trafiac
    crit = [r for r in rows if "6" in r["expected"] and not r["main_found"]]
    ok = main_pass >= int(0.8 * n) and not crit
    print(f"\nCRITICAL art.6 misses: {[r['id'] for r in crit] or 'NONE'}")
    print("RESULT:", "PASS" if ok else "REVIEW")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
