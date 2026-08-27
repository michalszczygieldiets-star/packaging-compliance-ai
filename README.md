# Packaging Compliance AI — PPWR (MVP)

Asystent RAG odpowiadajacy po polsku na pytania dzialu opakowan o wymagania
**Rozporzadzenia (UE) 2025/40 (PPWR)** — z podstawa prawna, cytatem, wyjatkami,
terminami i praktycznym znaczeniem. Dostepny przez przegladarke.

> **Status:** w budowie (Faza 2/17 — szkielet). Sekcje ponizej uzupelniane fazami.

## Architektura (skrot)
Legal-structure-aware RAG: canonical source → parser struktury prawnej →
legal-aware chunking → metadata + stable IDs → relacje (odeslania) →
embeddings/indeks → exact citation lookup + semantic search → context expansion →
LLM (Anthropic, structured output) → UI (Streamlit).

## Canonical source
Rozporzadzenie (UE) 2025/40 z 19.12.2024. Preferencja: oficjalny HTML EUR-Lex
(PL) → XML/Formex → fallback lokalny PDF. _(Wybor potwierdzany w Fazie 3.)_

## Struktura repo
```
app.py  ingest.py  rag.py  config.py  requirements.txt
README.md  MVP_REPORT.md  .gitignore  .env.example
data/raw/   index/
src/parser.py  src/chunker.py  src/retrieval.py  src/relations.py
src/embeddings.py  src/llm.py
tests/golden_questions.json
```

## Instalacja i uruchomienie _(do uzupelnienia w Fazie 7/13)_
```bash
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env   # uzupelnij sekrety
python ingest.py       # zbuduj indeks
streamlit run app.py   # uruchom UI
```

## Sekrety i bezpieczenstwo
Zadnych sekretow w repo. `.env` w `.gitignore`, `.env.example` bez wartosci.
Zero poufnych danych firmowych — zrodla wylacznie publiczne.

## Hosting i dostep
Streamlit + access gate na hasle aplikacji (`APP_PASSWORD`). Community Cloud
(darmowo) lub Render jako fallback. _(Weryfikacja platformy w Fazie 14.)_

## Ograniczenia i pozycjonowanie prawne
Narzedzie wspomaga wyszukiwanie i analize tresci regulacyjnych. Nie zastepuje
formalnej opinii prawnej ani oficjalnej oceny zgodnosci. Rozroznia wymagania juz
okreslone w PPWR od tych z przyszlych aktow delegowanych/wykonawczych.

## Roadmapa (migracja poza MVP)
Docker, FastAPI, PostgreSQL + pgvector / Qdrant, serwer firmowy, SSO,
wiele aktow prawnych, akty delegowane/wykonawcze, prawo krajowe.
