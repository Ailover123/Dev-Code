import time

import streamlit as st
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from coderagent.agent import run_agent


st.set_page_config(page_title="Dev-Code", page_icon="🧠", layout="wide")


# Shows one ReAct step with different styling based on the step type.
def show_step(step: dict) -> None:
    step_type = step["type"]
    content = step["content"]

    if step_type == "thought":
        st.info(f"Thought: {content}")
    elif step_type == "action":
        st.warning(f"Action: {content}")
    elif step_type == "observation":
        st.success(f"Observation:\n\n{content}")
    elif step_type == "final":
        st.subheader("Final Answer")
        st.code(content, language="python")


# Finds the final fixed code from the agent trace.
def get_final_code(steps: list[dict]) -> str:
    for step in reversed(steps):
        if step["type"] == "final":
            return step["content"]

    return ""


st.title("Dev-Code — ReAct Debugging Agent")

st.write(
    "Paste broken Python code and watch the agent run, inspect, fix, and verify it."
)

default_code = "print(10 / 0)"

broken_code = st.text_area(
    "Paste your broken Python code here",
    value=default_code,
    height=220,
)

if st.button("Debug with Agent"):
    if not broken_code.strip():
        st.error("Please paste some Python code first.")
    else:
        with st.spinner("Agent is debugging..."):
            steps = run_agent(broken_code)

        st.subheader("ReAct Trace")

        for step in steps:
            show_step(step)
            time.sleep(0.4)

        fixed_code = get_final_code(steps)

        if fixed_code and not fixed_code.startswith("The agent"):
            st.subheader("Fixed Code")
            st.code(fixed_code, language="python")