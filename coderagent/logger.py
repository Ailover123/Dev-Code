import json
from datetime import datetime

from coderagent.settings import get_trace_log_path

LOG_PATH = get_trace_log_path()


# Finds the final answer from a trace.
def get_final_code(steps: list[dict]) -> str:
    for step in reversed(steps):
        if step["type"] == "final":
            return step["content"]

    return ""


# Checks whether a trace used memory.
def used_memory(steps: list[dict]) -> bool:
    return any("search_memory" in step["content"] for step in steps)


# Checks whether a trace used Gemini.
def used_gemini(steps: list[dict]) -> bool:
    return any(step.get("agent") == "FixerAgent" for step in steps)


# Reads all completed debugging run logs.
def read_debug_runs() -> list[dict]:
    if not LOG_PATH.exists():
        return []

    runs = []

    with LOG_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            try:
                runs.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return runs


# Summarizes completed debugging run logs for API or dashboard views.
def summarize_runs(runs: list[dict]) -> dict:
    total_runs = len(runs)

    if total_runs == 0:
        return {
            "runs": 0,
            "successful_runs": 0,
            "memory_runs": 0,
            "gemini_runs": 0,
            "average_steps": 0,
            "average_time": 0,
        }

    return {
        "runs": total_runs,
        "successful_runs": sum(1 for run in runs if run.get("success")),
        "memory_runs": sum(1 for run in runs if run.get("used_memory")),
        "gemini_runs": sum(1 for run in runs if run.get("used_gemini")),
        "average_steps": round(sum(run.get("steps_count", 0) for run in runs) / total_runs, 2),
        "average_time": round(sum(run.get("time_elapsed", 0) for run in runs) / total_runs, 2),
    }


# Writes one completed debugging run to a JSONL log file.
def log_debug_run(input_code: str, steps: list[dict], elapsed: float, language: str = "auto") -> None:
    final_code = get_final_code(steps)

    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "language": language,
        "input_code": input_code,
        "fixed_code": final_code,
        "success": bool(final_code and not final_code.startswith("The generated fix failed")),
        "used_memory": used_memory(steps),
        "used_gemini": used_gemini(steps),
        "steps_count": len(steps),
        "time_elapsed": round(elapsed, 2),
    }

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")
