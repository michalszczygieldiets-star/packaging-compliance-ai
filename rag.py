"""
Orkiestracja RAG: spina retrieval + context expansion + LLM.

    answer_question(question) -> dict {answer: RagAnswer, citation, context, debug}

Uzywane przez app.py (UI) i CLI.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.llm import generate_answer  # noqa: E402
from src.retrieval import expand_context  # noqa: E402


def answer_question(question: str) -> dict:
    """Pelny przebieg: retrieve -> context expansion -> generate_answer."""
    exp = expand_context(question)
    context = exp["context"]
    answer = generate_answer(question, context)

    debug = {
        "citation": exp["citation"],
        "n_context": len(context),
        "added_refs": exp["added_refs"],
        "context_ids": [c["stable_chunk_id"] for c in context],
    }
    return {"answer": answer, "citation": exp["citation"],
            "context": context, "debug": debug}


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "Co mowi art. 6 ust. 3?"
    res = answer_question(q)
    print(res["answer"].model_dump_json(indent=2))
