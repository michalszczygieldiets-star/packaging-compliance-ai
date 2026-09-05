"""
FAZA 13 - Streamlit UI: "Packaging Compliance AI - PPWR".

Access gate na hasle aplikacji (APP_PASSWORD). Renderuje RagAnswer: podstawa
prawna, uzasadnienie, wyjatki, terminy, znaczenie praktyczne, rozwijane zrodla,
confidence, disclaimer. Historia w st.session_state. DEBUG_MODE ukryty przed
zwyklym uzytkownikiem.

Uruchamianie:  streamlit run app.py
"""
from __future__ import annotations

import os

import streamlit as st

# --- Most sekretow: na Streamlit Cloud sekrety sa w st.secrets; przenies je do
#     os.environ ZANIM zaimportujemy config (ktory czyta os.getenv). ---
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass

import config  # noqa: E402
from rag import answer_question  # noqa: E402

st.set_page_config(page_title="Packaging Compliance AI — PPWR", page_icon="♻️",
                   layout="centered")

DISCLAIMER = (
    "Narzędzie wspomaga wyszukiwanie i analizę treści regulacyjnych. "
    "Nie zastępuje formalnej opinii prawnej ani oficjalnej oceny zgodności."
)
INSUFFICIENT_MSG = (
    "Nie znalazłem wystarczającej podstawy w dostępnych źródłach, aby "
    "odpowiedzieć na to pytanie z odpowiednią pewnością."
)
CONF_BADGE = {"high": "🟢 wysoka", "medium": "🟡 średnia", "low": "🔴 niska"}


# ----------------------------------------------------------------- access gate
def _check_access() -> bool:
    if not config.APP_PASSWORD:
        st.info("Tryb otwarty (nie ustawiono APP_PASSWORD).")
        return True
    if st.session_state.get("_authed"):
        return True
    st.title("Packaging Compliance AI — PPWR")
    st.caption("Dostęp chroniony hasłem.")
    with st.form("login"):
        pwd = st.text_input("Hasło dostępu", type="password")
        entered = st.form_submit_button("Wejdź")
    if entered:
        if pwd == config.APP_PASSWORD:
            st.session_state["_authed"] = True
            st.rerun()
        else:
            st.error("Nieprawidłowe hasło.")
    return False


# ----------------------------------------------------------------- rendering
def _render_answer(res: dict):
    ans = res["answer"]

    if ans.insufficient_context:
        st.warning(INSUFFICIENT_MSG)
        if ans.answer:
            st.caption(ans.answer)
    else:
        st.markdown(f"### Odpowiedź &nbsp; {CONF_BADGE.get(ans.confidence, ans.confidence)}",
                    unsafe_allow_html=True)
        st.write(ans.answer)

    if ans.legal_basis:
        st.markdown("**📑 Podstawa prawna**")
        st.markdown("\n".join(f"- {x}" for x in ans.legal_basis))
    if ans.reasoning:
        st.markdown("**🧭 Uzasadnienie**")
        st.write(ans.reasoning)
    if ans.complementary_provisions:
        st.markdown("**🔗 Przepisy komplementarne**")
        st.markdown("\n".join(f"- {x}" for x in ans.complementary_provisions))
    if ans.exceptions:
        st.markdown("**⚠️ Wyjątki / odstępstwa**")
        st.markdown("\n".join(f"- {x}" for x in ans.exceptions))
    if ans.deadlines:
        st.markdown("**📅 Terminy**")
        st.markdown("\n".join(f"- {x}" for x in ans.deadlines))
    if ans.practical_implications:
        st.markdown("**🏭 Znaczenie praktyczne dla działu opakowań**")
        st.write(ans.practical_implications)

    if ans.quotes:
        with st.expander("📜 Cytaty ze źródeł"):
            for q in ans.quotes:
                st.markdown(f"> {q}")

    with st.expander("🗂 Źródła (fragmenty przekazane do analizy)"):
        for c in res["context"]:
            st.markdown(f"**{c.get('citation')}** &nbsp;`{c.get('legal_function')}`  "
                        f"<span style='color:gray'>{c.get('stable_chunk_id')}</span>",
                        unsafe_allow_html=True)
            st.caption((c.get("text") or "")[:600] + ("…" if len(c.get("text") or "") > 600 else ""))

    if config.DEBUG_MODE:
        with st.expander("🔧 DEBUG (retrieval)"):
            st.json(res["debug"])


# ----------------------------------------------------------------- main
def main():
    if not _check_access():
        return

    st.title("Packaging Compliance AI — PPWR")
    st.caption("MVP — odpowiedzi na podstawie Rozporządzenia (UE) 2025/40.")

    if "history" not in st.session_state:
        st.session_state["history"] = []

    with st.form("ask"):
        q = st.text_area("Pytanie o wymagania dla opakowań (po polsku)",
                         placeholder="np. Czy tacka PP do dania gotowego będzie mogła być używana po 2030?")
        submitted = st.form_submit_button("Zapytaj")

    if submitted and q.strip():
        with st.spinner("Analizuję źródła PPWR…"):
            try:
                res = answer_question(q.strip())
                st.session_state["history"].insert(0, (q.strip(), res))
            except RuntimeError as e:
                st.error(str(e))
            except Exception as e:  # noqa: BLE001
                # NIE pokazujemy pelnego tracebacka - moze zawierac sekret
                # (np. wartosc naglowka Authorization). Tylko typ + komunikat.
                st.error(f"Błąd analizy [{type(e).__name__}]: {e}")

    for i, (question, res) in enumerate(st.session_state["history"]):
        if i > 0:
            st.divider()
        st.markdown(f"#### ❓ {question}")
        _render_answer(res)

    st.divider()
    st.caption("⚖️ " + DISCLAIMER)


if __name__ == "__main__":
    main()
else:
    main()
