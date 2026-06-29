import json
from datetime import datetime
from pathlib import Path


LOG_PATH = Path("coderagent/traces.jsonl")


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
    return any(step["agent"] == "FixerAgent" for step in steps)


# Writes one completed debugging run to a JSONL log file.
def log_debug_run(input_code: str, steps: list[dict], elapsed: float) -> None:
    final_code = get_final_code(steps)

    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "input_code": input_code,
        "fixed_code": final_code,
        "success": bool(final_code and not final_code.startswith("The generated fix failed")),
        "used_memory": used_memory(steps),
        "used_gemini": used_gemini(steps),
        "steps_count": len(steps),
        "time_elapsed": round(elapsed, 2),
    }

    with LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")