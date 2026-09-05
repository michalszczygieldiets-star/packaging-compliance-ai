# MVP_REPORT — Packaging Compliance AI (PPWR)

## Executive summary
Proof-of-concept asystenta RAG odpowiadającego po polsku na pytania działu
opakowań o wymagania **Rozporządzenia (UE) 2025/40 (PPWR)**. System zwraca
odpowiedź z podstawą prawną (dokładne jednostki), uzasadnieniem, cytatami,
wyjątkami, terminami i praktycznym znaczeniem — wyłącznie na bazie retrieved
context, z guardrailami przeciw halucynacji podstawy prawnej. Dostęp przez
przeglądarkę (Streamlit), chroniony hasłem.

**Status: WDROŻONY i działający.** MVP jest live na Streamlit Community Cloud,
zweryfikowany z zewnętrznej przeglądarki (logowanie hasłem + 3 pytania z
poprawną podstawą prawną: art. 6 ust. 3 / klasy A-C, art. 9 / kompostowalne,
art. 48 / selektywna zbiórka).

## Architektura
Legal-structure-aware RAG (własny kod, bez LangChain/LlamaIndex):
1. **Canonical source** — oficjalny Formex-HTML EUR-Lex (PL), 1,32 MB.
2. **Parser** — struktura prawna po kotwicach `id` (71 artykułów, 13 załączników,
   188 motywów).
3. **Chunking** — legal-aware, granice jednostek przed rozmiarem tokenowym +
   `oversized_unit_rule`; 652 chunki ze stabilnymi ID i pełnymi metadanymi.
4. **Relacje** — 767 krawędzi odesłań (references/exception_to), z filtrem aktów
   zewnętrznych i rozwiązywaniem odesłań względnych.
5. **Retrieval** — exact citation lookup (deterministyczny) + hybryda
   semantic (FAISS) × BM25 (RRF).
6. **Context expansion** — dokłada references (art. 48, Zał. II/VII), pozostałe
   ustępy, w jawnym budżecie.
7. **LLM** — Anthropic Claude (`claude-opus-5`), structured output (Pydantic),
   guardrails w system prompt.
8. **UI** — Streamlit + access gate na haśle.

## Canonical source
Rozporządzenie (UE) 2025/40 z 19.12.2024 (PPWR). Format: oficjalny Formex-HTML
EUR-Lex (CELEX 32025R0040, wersja PL). Pobrany przez przeglądarkę (EUR-Lex
blokuje pobieranie skryptowe — HTTP 202/antybot). Walidacja: art. 6 i Załącznik
II czytelne, brak błędów kolejności tekstu.

## Wyniki walidacji parsera (BLOCKING sanity checks)
Wszystkie PASS: istnieją art. 1/6/65, Załącznik II; art. 6 ma poprawny tytuł
("Opakowania zdatne do recyklingu") i 12 wykrytych ustępów; odesłania art. 6 →
art. 48 i art. 6 → Załącznik II obecne.

## Wyniki golden dataset (retrieval)
24 pytania testowe. **Główna podstawa prawna: 24/24 (100%)** trafień w oczekiwane
źródło (exact + hybryda). Exact lookup: 2/2. Krytyczne pytania art. 6 (w tym
flagowy E2E „tacka PP po 2030"): wszystkie trafiają w art. 6. Hybryda BM25+RRF
naprawiła przypadki, gdzie czysty wektor dryfował semantycznie.

## Co działa
- Pełny pipeline ingestion (canonical → indeks) reprodukowalny.
- Exact citation lookup (warianty pisowni, numeracja rzymska, brak polskich znaków).
- Hybrydowy retrieval + context expansion z komplementarnymi jednostkami.
- Structured output + guardrails (kod gotowy).
- Streamlit UI z access gate, historią, panelem DEBUG.

## Co wymaga uwagi / ograniczenia
- **Embeddingi lokalne w RAM.** Domyślny model to `paraphrase-multilingual-
  MiniLM-L12-v2` (384d, ~0,22 GB) — mieści się na darmowym Streamlit Cloud i
  utrzymuje **24/24** na golden dzięki hybrydzie BM25. e5-large (2,2 GB) daje
  podobną jakość, ale wymaga hostingu z większym RAM (np. HF Spaces).
- **Akty delegowane/wykonawcze poza bazą.** Wiele wymagań art. 6 (kryteria DfR,
  klasy, progi) ma być doprecyzowanych w przyszłych aktach — system to sygnalizuje
  i NIE generuje ich treści.
- **Tabele w załącznikach** renderowane jako tekst (cell | cell) — wyszukiwalne,
  ale bez układu wizualnego.
- **Jeden akt prawny.** Brak prawa krajowego, orzecznictwa, procedur firmowych.

## Ryzyka prawne i techniczne
- Narzędzie wspomagające, nie porada prawna — finalna zgodność wymaga weryfikacji.
- Python 3.14 — stack zweryfikowany (fastembed/faiss/bs4 działają lokalnie i na
  Streamlit Cloud).
- Lekcja z deploymentu: sekret wklejony w panelu hostingu miewa końcową
  spację/nową linię → `Illegal header value` → `APIConnectionError`. Rozwiązane
  przez `.strip()` sekretów w `config.py`.
- Bezpieczeństwo: nie wyświetlać pełnych tracebacków w UI (mogą zawierać wartość
  nagłówka Authorization = klucz). W MVP usunięto; przy incydencie ekspozycji
  klucza — rotacja w Anthropic Console.

## Koszty MVP
- Embeddingi: lokalne, keyless (0 zł).
- LLM: Anthropic per-token; kontrola przez spend cap w Console. Demo ~grosze.
- Hosting: darmowy tier (Streamlit Community Cloud / HF Spaces).

## Następne kroki / przed użyciem produkcyjnym
- Rozszerzenie golden dataset i przegląd prawny odpowiedzi przez eksperta.
- Migracja embeddingów na API (Voyage) lub serwer firmowy (patrz roadmapa README).
- Dodanie aktów delegowanych/wykonawczych po ich publikacji.
- Integracja z infrastrukturą firmy (SSO, kontrola dostępu) — poza MVP.
