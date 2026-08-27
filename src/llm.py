"""
FAZY 11 + 12 - Warstwa LLM (Anthropic) + guardrails.

Odseparowana od UI i retrievalu przez abstrakcje:
    generate_answer(question, sources) -> RagAnswer
Structured output walidowany Pydantikiem. System prompt wymusza:
odpowiadaj wylacznie z retrieved context; kazda teza prawna ma zrodlo;
oddzielaj motywy od norm; zachowuj warunkowe daty; przy braku podstawy
ustaw insufficient_context=true.
"""
from __future__ import annotations


def generate_answer(question, sources):
    """Zwraca RagAnswer (structured) na podstawie pytania i zrodel."""
    raise NotImplementedError("Do zbudowania w Fazie 11.")
