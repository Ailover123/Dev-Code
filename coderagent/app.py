import html
import sys
import time
from pathlib import Path
import json

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from coderagent.agents.orchestrator import run_a2a_debug
from coderagent.logger import log_debug_run

TRACE_LOG_PATH = ROOT_DIR / "coderagent" / "traces.jsonl"

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

    .trace-content pre {
        margin: 0;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        font: inherit;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Reads saved trace logs from the JSONL log file.
def read_trace_logs() -> list[dict]:
    if not TRACE_LOG_PATH.exists():
        return []

    logs = []

    with TRACE_LOG_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    return logs

# Shows simple LLMOps metrics from previous debug runs.
def show_llmops_dashboard() -> None:
    logs = read_trace_logs()

    if not logs:
        st.info("No trace logs yet. Run the FastAPI /debug endpoint first.")
        return

    total_runs = len(logs)
    successful_runs = sum(1 for log in logs if log["success"])
    memory_runs = sum(1 for log in logs if log["used_memory"])
    gemini_runs = sum(1 for log in logs if log["used_gemini"])
    average_steps = sum(log["steps_count"] for log in logs) / total_runs
    average_time = sum(log["time_elapsed"] for log in logs) / total_runs

    metric_cols = st.columns(6)
    metric_cols[0].metric("Runs", total_runs)
    metric_cols[1].metric("Success", f"{successful_runs}/{total_runs}")
    metric_cols[2].metric("Memory", memory_runs)
    metric_cols[3].metric("Gemini", gemini_runs)
    metric_cols[4].metric("Avg Steps", f"{average_steps:.1f}")
    metric_cols[5].metric("Avg Time", f"{average_time:.2f}s")

    st.subheader("Recent Runs")

    recent_runs = []

    for log in reversed(logs[-8:]):
        recent_runs.append({
            "Time": log["timestamp"],
            "Success": log["success"],
            "Memory": log["used_memory"],
            "Gemini": log["used_gemini"],
            "Steps": log["steps_count"],
            "Seconds": log["time_elapsed"],
            "Input": log["input_code"][:80],
        })

    st.dataframe(recent_runs, use_container_width=True, hide_index=True)

# Shows one ReAct step as a readable card in the trace.
def show_step(step: dict) -> None:
    step_type = step["type"]
    content = html.escape(step["content"]).replace("#", "&#35;")
    agent = step.get("agent", "Dev-Code Agent")
    label = f"{agent} - {step_type.upper()}"

    st.markdown(
        f"""
        <div class="trace-card {step_type}">
            <div class="trace-label">{label}</div>
            <div class="trace-content"><pre>{content}</pre></div>
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
def get_run_status(fixed_code: str) -> str:
    if fixed_code and not fixed_code.startswith("The agent"):
        return "Success"

    return "Failed"

def get_error_type(steps: list[dict]) -> str:
    for step in reversed(steps):
        if step["type"] == "observation" and "Error Type:" in step["content"]:
            for line in step["content"].splitlines():
                if line.startswith("Error Type:"):
                    return line.replace("Error Type:", "").strip()

    return "None"

def build_markdown_report(input_code: str, fixed_code: str, steps: list[dict], elapsed: float, success: bool) -> str:
    status = "Success" if success else "Failed"

    lines = [
        "# Dev-Code Debug Report",
        "",
        f"Status: {status}",
        f"Time: {elapsed:.1f}s",
        "",
        "## Original Code",
        "",
        "```python",
        input_code,
        "```",
        "",
        "## ReAct Trace",
        "",
    ]

    for step in steps:
        label = step["type"].title()
        lines.append(f"### {label}")
        lines.append("")
        lines.append("```text")
        lines.append(step["content"])
        lines.append("```")
        lines.append("")

    lines.extend([
        "## Fixed Code",
        "",
        "```python",
        fixed_code,
        "```",
        "",
    ])

    return "\n".join(lines)

if "history" not in st.session_state:
    st.session_state["history"] = []

if "debug_code" not in st.session_state:
    st.session_state["debug_code"] = "print(10 / 0)"


# Loads a previous session's code into the debugger editor.
def load_history_code(code: str) -> None:
    st.session_state["debug_code"] = code


st.markdown(
    '<div class="app-title">Dev-Code - A2A ReAct Debugging Agent</div>',
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="app-subtitle">
       Paste broken Python code and watch specialist agents analyze, fix, verify, and remember debugging patterns.
    </div>
    """,
    unsafe_allow_html=True,
)

debug_tab, dashboard_tab = st.tabs(["Debugger", "LLMOps Dashboard"])

with debug_tab:
    broken_code = st.text_area(
        "Broken Python code",
        key="debug_code",
        height=220,
    )

    run_clicked = st.button("Debug with Agent", type="primary")

    if run_clicked:
        if not broken_code.strip():
            st.error("Please paste some Python code first.")
        else:
            started_at = time.perf_counter()

            with st.spinner("Agent is debugging..."):
                steps = run_a2a_debug(broken_code)

            elapsed = time.perf_counter() - started_at
            fixed_code = get_final_code(steps)
            status = get_run_status(fixed_code)
            error_type = get_error_type(steps)

            success = status == "Success"

            markdown_report = build_markdown_report(
                input_code=broken_code,
                fixed_code=fixed_code,
                steps=steps,
                elapsed=elapsed,
                success=success,
            )

            st.session_state["history"].append({
                "input_code": broken_code,
                "fixed_code": fixed_code,
                "steps": steps,
                "time": elapsed,
                "success": success,
            })

            log_debug_run(broken_code, steps, elapsed)

            metric_cols = st.columns(5)
            metric_cols[0].metric("Status", status)
            metric_cols[1].metric("Steps", len(steps))
            metric_cols[2].metric("Tool Calls", count_steps(steps, "action"))
            metric_cols[3].metric("Thoughts", count_steps(steps, "thought"))
            metric_cols[4].metric("Time", f"{elapsed:.1f}s")

            if status == "Failed":
                st.warning(f"Final error type: {error_type}")

            st.subheader("ReAct Trace")

            for step in steps:
                show_step(step)

            if fixed_code and not fixed_code.startswith("The agent"):
                st.subheader("Fixed Code")
                st.code(fixed_code, language="python")

            st.download_button(
                label="Download Debug Report",
                data=markdown_report,
                file_name="dev-code-debug-report.md",
                mime="text/markdown",
            )

with dashboard_tab:
    show_llmops_dashboard()

st.sidebar.header("Session History")

if not st.session_state["history"]:
    st.sidebar.caption("No debug sessions yet.")
else:
    for index, session in enumerate(reversed(st.session_state["history"]), start=1):
        status = "Success" if session["success"] else "Failed"

        with st.sidebar.expander(f"Run {index} - {status}"):
            st.caption(f"Time: {session['time']:.1f}s")
            st.code(session["input_code"], language="python")
            st.button(
                "Load Code",
                key=f"load_history_{index}",
                on_click=load_history_code,
                args=(session["input_code"],),
            )
