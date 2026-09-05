# Packaging Compliance AI — PPWR (MVP)

Asystent RAG odpowiadający po polsku na pytania działu opakowań o wymagania
**Rozporządzenia (UE) 2025/40 (PPWR)** — z podstawą prawną (dokładne jednostki),
uzasadnieniem, cytatem, wyjątkami, terminami i praktycznym znaczeniem. Dostępny
przez przeglądarkę, chroniony hasłem.

> **To narzędzie wspomagające**, nie porada prawna. Nie zastępuje formalnej
> opinii prawnej ani oficjalnej oceny zgodności.

## Architektura (skrót)
Legal-structure-aware RAG (własny kod, bez LangChain/LlamaIndex):
canonical source (Formex-HTML EUR-Lex) → [parser](src/parser.py) struktury
prawnej → legal-aware [chunking](src/chunker.py) + metadata + stable IDs →
[relacje](src/relations.py) (odesłania) → [embeddings](src/embeddings.py)/FAISS →
exact citation lookup + hybryda semantic×BM25 ([retrieval](src/retrieval.py)) →
context expansion → [LLM](src/llm.py) (Anthropic, structured output) →
[UI](app.py) (Streamlit).

Szczegółowe wyniki: [MVP_REPORT.md](MVP_REPORT.md).

## Canonical source
Rozporządzenie (UE) 2025/40 (PPWR), oficjalny Formex-HTML EUR-Lex (PL, CELEX
32025R0040) w [data/raw/ppwr_pl.html](data/raw/ppwr_pl.html). Indeks jest
zbudowany i wersjonowany w `index/` — deploy nie przebudowuje go od zera.

## Struktura repo
```
app.py  ingest.py  rag.py  config.py  requirements.txt
README.md  MVP_REPORT.md  .gitignore  .env.example
data/raw/ppwr_pl.html      index/ (chunks, vectors.faiss, relations, id_map)
src/parser.py  src/chunker.py  src/relations.py
src/embeddings.py  src/retrieval.py  src/llm.py
tests/golden_questions.json  tests/eval_golden.py  tests/validate_parser.py
.streamlit/config.toml  .streamlit/secrets.toml.example
```

## Uruchomienie lokalne
```bash
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env          # uzupełnij ANTHROPIC_API_KEY i APP_PASSWORD

python ingest.py              # (opcjonalnie) przebuduj indeks z canonical source
streamlit run app.py          # UI na http://localhost:8501
```

Testy:
```bash
python tests/validate_parser.py   # BLOCKING sanity checks parsera
python tests/eval_golden.py       # ewaluacja retrievalu (golden dataset)
```

## Sekrety i bezpieczeństwo
Żadnych sekretów w repo. `.env` i `.streamlit/secrets.toml` w `.gitignore`;
`.env.example` / `secrets.toml.example` bez wartości. Zero poufnych danych
firmowych — źródła wyłącznie publiczne. **Ustaw spend cap w Anthropic Console.**

## Deployment (Streamlit Community Cloud — darmowy)
1. Wypchnij repo na GitHub (prywatne).
2. [share.streamlit.io](https://share.streamlit.io) → New app → wskaż repo i `app.py`.
3. **Settings → Secrets** → wklej zawartość wg
   [.streamlit/secrets.toml.example](.streamlit/secrets.toml.example)
   (`ANTHROPIC_API_KEY`, `APP_PASSWORD`, `ANTHROPIC_MODEL`). Sekrety trafiają do
   `os.environ`, skąd czyta je `config.py`.
4. Deploy. Dostęp chroni hasło aplikacji (`APP_PASSWORD`).

> **Pamięć RAM.** Model embeddingów ładuje się do RAM przy każdym zapytaniu.
> Domyślny `intfloat/multilingual-e5-large` (2,2 GB) przekracza darmowy tier
> Streamlit (~1 GB) — do darmowego hostingu użyj mniejszego modelu przez env
> `LOCAL_EMBEDDING_MODEL` (patrz MVP_REPORT) i przebuduj indeks, albo hostuj tam,
> gdzie jest więcej RAM (HF Spaces free = 16 GB).

## Ograniczenia
Jeden akt prawny; akty delegowane/wykonawcze poza bazą (system to sygnalizuje,
nie zgaduje ich treści); tabele załączników jako tekst. Pełna lista w MVP_REPORT.

## Roadmapa (migracja poza MVP)
Docker, FastAPI, PostgreSQL + pgvector / Qdrant, embeddingi przez API (Voyage) lub
serwer firmowy, SSO, wiele aktów prawnych, akty delegowane/wykonawcze, prawo
krajowe, procedury wewnętrzne.
