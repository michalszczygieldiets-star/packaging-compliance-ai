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

    load_dotenv()
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
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "voyage")  # voyage | local
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-3.5")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")

TOP_K = 8                    # ile kandydatow z semantic search
CONTEXT_BUDGET_CHUNKS = 12   # jawny budzet kontekstu przekazywanego do LLM

# =============================================================
#  LLM (Anthropic)
# =============================================================
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

# =============================================================
#  Aplikacja / dostep
# =============================================================
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").strip().lower() in {"1", "true", "yes"}
