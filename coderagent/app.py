import html
import sys
import time
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from coderagent.agent import run_agent


st.set_page_config(page_title="Dev-Code", layout="wide")

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        max-width: 1180px;
    }

    .app-kicker {
        color: #8b949e;
        font-size: 0.9rem;
        margin-bottom: 0.35rem;
    }

    .app-title {
        font-size: 2.1rem;
        font-weight: 750;
        margin-bottom: 0.35rem;
    }

    .app-subtitle {
        color: #c9d1d9;
        max-width: 760px;
        margin-bottom: 1.5rem;
    }

    .trace-card {
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.75rem;
        line-height: 1.5;
    }

    .trace-label {
        font-size: 0.72rem;
        font-weight: 750;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }

    .thought {
        background: rgba(56, 139, 253, 0.12);
        border-color: rgba(56, 139, 253, 0.35);
    }

    .thought .trace-label {
        color: #79c0ff;
    }

    .action {
        background: rgba(210, 153, 34, 0.12);
        border-color: rgba(210, 153, 34, 0.38);
    }

    .action .trace-label {
        color: #f2cc60;
    }

    .observation {
        background: rgba(46, 160, 67, 0.13);
        border-color: rgba(46, 160, 67, 0.4);
    }

    .observation .trace-label {
        color: #7ee787;
    }

    .final {
        background: rgba(163, 113, 247, 0.12);
        border-color: rgba(163, 113, 247, 0.35);
    }

    .final .trace-label {
        color: #d2a8ff;
    }

    .trace-content {
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        font-size: 0.92rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Shows one ReAct step as a readable card in the trace.
def show_step(step: dict) -> None:
    step_type = step["type"]
    content = html.escape(step["content"])
    label = step_type.upper()

    st.markdown(
        f"""
        <div class="trace-card {step_type}">
            <div class="trace-label">{label}</div>
            <div class="trace-content">{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Finds the final fixed code from the agent trace.
def get_final_code(steps: list[dict]) -> str:
    for step in reversed(steps):
        if step["type"] == "final":
            return step["content"]

    return ""


# Counts visible agent steps by type for the small metric row.
def count_steps(steps: list[dict], step_type: str) -> int:
    return sum(1 for step in steps if step["type"] == step_type)


st.markdown('<div class="app-kicker">CoderAgent MVP</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-title">Dev-Code - ReAct Debugging Agent</div>',
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="app-subtitle">
        Paste broken Python code and watch the agent run it, inspect the error,
        search context, suggest a fix, and verify the result.
    </div>
    """,
    unsafe_allow_html=True,
)

default_code = "print(10 / 0)"

broken_code = st.text_area(
    "Broken Python code",
    value=default_code,
    height=220,
)

run_clicked = st.button("Debug with Agent", type="primary")

if run_clicked:
    if not broken_code.strip():
        st.error("Please paste some Python code first.")
    else:
        started_at = time.perf_counter()

        with st.spinner("Agent is debugging..."):
            steps = run_agent(broken_code)

        elapsed = time.perf_counter() - started_at
        fixed_code = get_final_code(steps)

        metric_cols = st.columns(4)
        metric_cols[0].metric("Steps", len(steps))
        metric_cols[1].metric("Actions", count_steps(steps, "action"))
        metric_cols[2].metric("Observations", count_steps(steps, "observation"))
        metric_cols[3].metric("Time", f"{elapsed:.1f}s")

        st.subheader("ReAct Trace")

        for step in steps:
            show_step(step)
            time.sleep(0.25)

        if fixed_code and not fixed_code.startswith("The agent"):
            st.subheader("Fixed Code")
            st.code(fixed_code, language="python")
