"""
Orkiestracja RAG: spina retrieval + context expansion + LLM.

    answer_question(question) -> dict {answer: RagAnswer, citation, context, debug}

Uzywane przez app.py (UI) i CLI.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import SCOPE_MIN_SIMILARITY  # noqa: E402
from src.llm import RagAnswer, generate_answer  # noqa: E402
from src.retrieval import expand_context, parse_citation, semantic_search  # noqa: E402

OFF_TOPIC_MSG = (
    "To pytanie wydaje się nie dotyczyć Rozporządzenia (UE) 2025/40 (PPWR). "
    "Asystent odpowiada wyłącznie na pytania o wymagania dla opakowań wynikające z PPWR."
)


def _in_scope(question: str) -> tuple[bool, float]:
    """Tani guardrail zakresu (bez LLM). Jawny cytat -> zawsze w zakresie;
    inaczej sprawdza najlepsze podobienstwo semantyczne wzgledem progu."""
    if parse_citation(question):
        return True, 1.0
    hits = semantic_search(question, top_k=1)
    top_cos = hits[0][1] if hits else 0.0
    return top_cos >= SCOPE_MIN_SIMILARITY, top_cos


def answer_question(question: str) -> dict:
    """Pelny przebieg: guardrail zakresu -> retrieve -> expansion -> LLM.
    Pytania spoza PPWR sa odcinane PRZED wywolaniem LLM (zero kosztu)."""
    in_scope, top_cos = _in_scope(question)
    if not in_scope:
        answer = RagAnswer(answer=OFF_TOPIC_MSG, confidence="low",
                           insufficient_context=True)
        return {"answer": answer, "citation": None, "context": [],
                "debug": {"gated_off_topic": True, "top_similarity": round(top_cos, 3)}}

    exp = expand_context(question)
    context = exp["context"]
    answer = generate_answer(question, context)

    debug = {
        "citation": exp["citation"],
        "n_context": len(context),
        "added_refs": exp["added_refs"],
        "context_ids": [c["stable_chunk_id"] for c in context],
        "top_similarity": round(top_cos, 3),
    }
    return {"answer": answer, "citation": exp["citation"],
            "context": context, "debug": debug}


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "Co mowi art. 6 ust. 3?"
    res = answer_question(q)
    print(res["answer"].model_dump_json(indent=2))
