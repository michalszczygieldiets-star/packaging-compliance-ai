"""
FAZA 4 - BLOCKING sanity checks parsera (sekcja 17 kontraktu).
Uruchom:  python tests/validate_parser.py
Wyjscie ASCII-safe (Windows console), exit code 1 przy FAIL.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.parser import parse_source  # noqa: E402


def main() -> int:
    doc = parse_source(str(ROOT / "data" / "raw" / "ppwr_pl.html"))
    arts = {a["article"]: a for a in doc["articles"]}
    annx = {a["annex"] for a in doc["annexes"]}

    nums = sorted((int(a["article"]) for a in doc["articles"] if a["article"]))
    print(f"articles={len(doc['articles'])} range={nums[0]}..{nums[-1]} "
          f"annexes={len(annx)} recitals={len(doc['recitals'])}")
    print("annexes:", ",".join(sorted(annx, key=_roman)))

    checks = []
    checks.append(("art_1_exists", "1" in arts))
    checks.append(("art_6_exists", "6" in arts))
    checks.append(("art_65_exists", "65" in arts))
    checks.append(("annex_II_exists", "II" in annx))

    a6 = arts.get("6", {})
    title = (a6.get("article_title") or "").lower()
    checks.append(("art_6_title_ok", "zdatne do recyklingu" in title))

    paras = a6.get("paragraphs", [])
    pnums = [p["paragraph"] for p in paras]
    checks.append(("art_6_has_paragraphs", len(paras) >= 10))
    checks.append(("art_6_para_1_12", pnums[:1] == ["1"] and "12" in pnums))

    # tresc kluczowa art. 6 (warunkowe daty, klasy, odeslania) faktycznie w tekscie
    joined = " ".join(p["text"] for p in paras).lower()
    # tolerancja na polska deklinacje: zalacznik / zalaczniku / zalaczniki II
    checks.append(("art_6_mentions_annex_II",
                   bool(re.search(r"załącznik\w*\s+ii\b", joined))))
    checks.append(("art_6_mentions_art_48", "art. 48" in joined))
    checks.append(("art_6_conditional_date", "późniejsza" in joined and "2030" in joined))

    print("--- SANITY CHECKS ---")
    ok = True
    for name, res in checks:
        print(f"  {name}: {'PASS' if res else 'FAIL'}")
        ok = ok and res

    print(f"art_6 title: {a6.get('article_title')!r}")
    print(f"art_6 paragraphs: {len(paras)} (numbers: {pnums})")
    print(f"RESULT: {'ALL PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def _roman(s):
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    for i, ch in enumerate(s):
        v = vals.get(ch, 0)
        nxt = vals.get(s[i + 1], 0) if i + 1 < len(s) else 0
        total += -v if v < nxt else v
    return total


if __name__ == "__main__":
    sys.exit(main())
