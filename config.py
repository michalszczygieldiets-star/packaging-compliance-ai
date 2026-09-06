"""
Centralna konfiguracja projektu Packaging Compliance AI (PPWR MVP).

Jedno miejsce na sciezki, nazwy modeli, budzety i progi.
Sekrety czytane sa ze srodowiska (.env) - nigdy nie sa hardkodowane.
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Wczytanie .env, jesli dostepny python-dotenv (opcjonalne) ---
try:
    from dotenv import load_dotenv

    # override=True: .env jest nadrzedny nad ewentualnym starym globalnym
    # ANTHROPIC_API_KEY w srodowisku systemowym (inaczej Streamlit bral stary
    # klucz -> 401). Sciezka wprost, by dzialalo niezaleznie od cwd.
    load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)
except Exception:
    pass

# =============================================================
#  Sciezki
# =============================================================
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"          # surowe zrodlo (PDF/HTML/XML) - nie w repo
INDEX_DIR = ROOT / "index"         # zbudowany indeks + chunki (regenerowalne)
TESTS_DIR = ROOT / "tests"

CHUNKS_PATH = INDEX_DIR / "chunks.json"          # jednostki prawne + metadata
VECTOR_INDEX_PATH = INDEX_DIR / "vectors"        # baza wektorowa (FAISS/Chroma)
RELATIONS_PATH = INDEX_DIR / "relations.json"    # graf odeslan miedzy jednostkami

# =============================================================
#  Dokument zrodlowy (canonical source)
# =============================================================
DOCUMENT_ID = "EU_2025_40"
# Prefiks stabilnych ID chunkow wg kontraktu (sekcja 6): bez podkreslnika,
# np. EU2025_40_ART6_P3. Rozny od DOCUMENT_ID celowo.
STABLE_ID_PREFIX = "EU2025_40"
DOCUMENT_TITLE = "Rozporzadzenie (UE) 2025/40"
# Oficjalny HTML PL (Plan A). Fallback: lokalny PDF w RAW_DIR (Plan B).
EURLEX_HTML_URL_PL = (
    "https://eur-lex.europa.eu/legal-content/PL/TXT/HTML/?uri=OJ:L_202500040"
)

# =============================================================
#  Chunking (legal-structure-aware)
# =============================================================
# Miekki gorny limit rozmiaru jednostki zanim zadziala oversized_unit_rule.
MAX_CHUNK_TOKENS = 800
# Twardy limit dla technicznego splitu jako ostatecznosci.
HARD_SPLIT_TOKENS = 1200

# =============================================================
#  Embeddings / retrieval (finalny wybor providera w Fazie 7)
# =============================================================
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")  # local | voyage
# Lokalny model (fastembed / ONNX, bez torcha, keyless). e5 wymaga prefiksow
# "query:"/"passage:". Na deployment mozna zejsc do lzejszego multilingual.
# MiniLM-L12 (384d, ~0.22 GB) - miesci sie na darmowym hostingu i utrzymuje
# 24/24 na golden dziecki hybrydzie BM25. e5-large (2,2 GB) daje podobna jakosc,
# ale nie miesci sie w ~1 GB RAM darmowego Streamlit Cloud.
LOCAL_EMBEDDING_MODEL = os.getenv(
    "LOCAL_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-3.5")  # gdy provider=voyage
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")

VECTOR_FAISS_PATH = INDEX_DIR / "vectors.faiss"
ID_MAP_PATH = INDEX_DIR / "id_map.json"
EMB_META_PATH = INDEX_DIR / "emb_meta.json"

TOP_K = 8                    # ile kandydatow z semantic search
CONTEXT_BUDGET_CHUNKS = 12   # jawny budzet kontekstu przekazywanego do LLM

# Guardrail zakresu (oszczednosc): jesli brak jawnego cytatu I najlepsze
# podobienstwo semantyczne < progu -> pytanie odcinane PRZED LLM (zero kosztu).
# Prog CELOWO niski (0.50): pytania zlozone/potoczne na temat maja niski cosinus
# (np. flagowe pytanie o catering 0.56, "tacka PP" 0.63) i NIE moga byc blokowane.
# 0.50 lapie oczywiste off-topic (pogoda, sport, IT ~0.1-0.3) bez falszywych
# blokad legit; pytania graniczne (np. VAT 0.63) przepuszcza do taniego guardraila
# LLM (krotka odpowiedz "brak podstawy"). Konfigurowalny przez env.
SCOPE_MIN_SIMILARITY = float(os.getenv("SCOPE_MIN_SIMILARITY", "0.50"))

# =============================================================
#  LLM (Anthropic)
# =============================================================
# .strip() KLUCZOWE: sekret wklejony w panelu hostingu miewa koncowa spacje/nowa
# linie -> "Illegal header value" w httpx -> APIConnectionError. Strip to naprawia.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
# Domyslnie Sonnet 5 - najlepszy stosunek jakosci do ceny i zwiezly (opus bywa
# nadmiernie gadatliwy przy zlozonych pytaniach -> uciecia + wysoki koszt).
# Mozna nadpisac na claude-opus-5 przez ANTHROPIC_MODEL, ale to droga opcja.
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5").strip()

# =============================================================
#  Aplikacja / dostep
# =============================================================
APP_PASSWORD = os.getenv("APP_PASSWORD", "").strip()
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").strip().lower() in {"1", "true", "yes"}
