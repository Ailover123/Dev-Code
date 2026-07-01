import html
import sys
import time
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from coderagent.agents.orchestrator import run_a2a_debug
from coderagent.lang_registry import list_supported_languages
from coderagent.logger import log_debug_run
from coderagent.logger import read_debug_runs, summarize_runs

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
    return read_debug_runs()

# Shows simple LLMOps metrics from previous debug runs.
def show_llmops_dashboard() -> None:
    logs = read_trace_logs()

    if not logs:
        st.info("No trace logs yet. Run the FastAPI /debug endpoint first.")
        return

    metrics = summarize_runs(logs)

    metric_cols = st.columns(6)
    metric_cols[0].metric("Runs", metrics["runs"])
    metric_cols[1].metric("Success", f"{metrics['successful_runs']}/{metrics['runs']}")
    metric_cols[2].metric("Memory", metrics["memory_runs"])
    metric_cols[3].metric("Gemini", metrics["gemini_runs"])
    metric_cols[4].metric("Avg Steps", f"{metrics['average_steps']:.1f}")
    metric_cols[5].metric("Avg Time", f"{metrics['average_time']:.2f}s")

    st.subheader("Recent Runs")

    recent_runs = []

    for log in reversed(logs[-8:]):
        recent_runs.append({
            "Time": log.get("timestamp", ""),
            "Success": log.get("success", False),
            "Memory": log.get("used_memory", False),
            "Gemini": log.get("used_gemini", False),
            "Steps": log.get("steps_count", 0),
            "Seconds": log.get("time_elapsed", 0),
            "Language": log.get("language", "auto"),
            "Input": log.get("input_code", "")[:80],
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
    failure_prefixes = (
        "The generated fix failed",
        "The agent",
        "Language detected but runner",
    )

    if fixed_code and not fixed_code.startswith(failure_prefixes):
        return "Success"

    return "Failed"



def get_error_type(steps: list[dict]) -> str:
    for step in reversed(steps):
        if step["type"] == "observation" and "Error Type:" in step["content"]:
            for line in step["content"].splitlines():
                if line.startswith("Error Type:"):
                    return line.replace("Error Type:", "").strip()

    return "None"


def get_user_goal(steps: list[dict]) -> str:
    for step in steps:
        if step["type"] == "thought" and step.get("agent") == "OrchestratorAgent" and step["content"].startswith("User requested:"):
            return step["content"].replace("User requested:", "", 1).strip()

    return ""


def build_markdown_report(
    input_code: str,
    fixed_code: str,
    steps: list[dict],
    elapsed: float,
    success: bool,
    user_goal: str = "",
) -> str:
    status = "Success" if success else "Failed"

    lines = [
        "# Dev-Code Debug Report",
        "",
        f"Status: {status}",
        f"Time: {elapsed:.1f}s",
        "",
    ]

    if user_goal.strip():
        lines.extend([
            "## User Goal",
            "",
            user_goal.strip(),
            "",
        ])

    lines.extend([
        "## Original Code",
        "",
        "```python",
        input_code,
        "```",
        "",
        "## ReAct Trace",
        "",
    ])

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

if "debug_language" not in st.session_state:
    st.session_state["debug_language"] = "auto"


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
    language_options = {
        "Auto": "auto",
        "Python": "python",
        "JavaScript": "javascript",
        "PHP": "php",
        "Ruby": "ruby",
        "Perl": "perl",
        "Lua": "lua",
        "TypeScript": "typescript",
    }

    selected_language = st.selectbox(
        "Language",
        options=list(language_options.keys()),
        key="debug_language_label",
    )
    debug_language = language_options[selected_language]
    st.session_state["debug_language"] = debug_language

    broken_code = st.text_area(
        "Broken code",
        key="debug_code",
        height=220,
    )

    user_goal = st.text_area(
        "What do you want? (optional)",
        key="user_goal",
        height=90,
        placeholder="Example: keep the same behavior but make the code easier to read",
    )

    run_clicked = st.button("Debug with Agent", type="primary")

    if run_clicked:
        if not broken_code.strip():
            st.error("Please paste some code first.")
        else:
            started_at = time.perf_counter()

            with st.spinner("Agent is debugging..."):
                steps = run_a2a_debug(broken_code, debug_language, user_goal)

            elapsed = time.perf_counter() - started_at
            fixed_code = get_final_code(steps)
            status = get_run_status(fixed_code)
            error_type = get_error_type(steps)
            trace_goal = get_user_goal(steps)

            success = status == "Success"

            markdown_report = build_markdown_report(
                input_code=broken_code,
                fixed_code=fixed_code,
                steps=steps,
                elapsed=elapsed,
                success=success,
                user_goal=trace_goal,
            )

            st.session_state["history"].append({
                "input_code": broken_code,
                "language": debug_language,
                "fixed_code": fixed_code,
                "steps": steps,
                "time": elapsed,
                "success": success,
                "user_goal": user_goal,
            })

            log_debug_run(broken_code, steps, elapsed, debug_language, user_goal)

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
                st.code(fixed_code, language="javascript" if debug_language == "javascript" else "python")

            st.download_button(
                label="Download Debug Report",
                data=markdown_report,
                file_name="dev-code-debug-report.md",
                mime="text/markdown",
            )

with dashboard_tab:
    show_llmops_dashboard()

with st.sidebar.expander("Supported languages", expanded=False):
    supported_languages = list_supported_languages()

    if not supported_languages:
        st.caption("No languages registered yet.")
    else:
        for language_info in supported_languages:
            status_label = "verified" if language_info["verified"] else "learned"
            st.caption(f"{language_info['name']} — {language_info['runner']} ({status_label})")

st.sidebar.header("Session History")

if not st.session_state["history"]:
    st.sidebar.caption("No debug sessions yet.")
else:
    for index, session in enumerate(reversed(st.session_state["history"]), start=1):
        status = "Success" if session["success"] else "Failed"

        with st.sidebar.expander(f"Run {index} - {status}"):
            st.caption(f"Time: {session['time']:.1f}s")
            st.caption(f"Language: {session.get('language', 'auto')}")
            if session.get("user_goal"):
                st.caption(f"Goal: {session['user_goal']}")
            st.code(
                session["input_code"],
                language="javascript" if session.get("language") == "javascript" else "python",
            )
            st.button(
                "Load Code",
                key=f"load_history_{index}",
                on_click=load_history_code,
                args=(session["input_code"],),
            )
