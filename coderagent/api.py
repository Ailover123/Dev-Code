from fastapi import FastAPI
from pydantic import BaseModel

from coderagent.agents.orchestrator import run_a2a_debug
import time
from coderagent.logger import log_debug_run

app = FastAPI(title="Dev-Code API")


class DebugRequest(BaseModel):
    code: str


# Returns the final answer from the trace.
def get_final_code(steps: list[dict]) -> str:
    for step in reversed(steps):
        if step["type"] == "final":
            return step["content"]

    return ""


# Checks whether the final trace result is a successful code fix.
def is_successful_trace(steps: list[dict]) -> bool:
    final_code = get_final_code(steps)

    return bool(final_code and not final_code.startswith("The generated fix failed"))


@app.get("/")
def health_check() -> dict:
    return {
        "status": "ok",
        "service": "Dev-Code API",
    }


@app.post("/debug")
def debug_code(request: DebugRequest) -> dict:
    started_at = time.perf_counter()

    steps = run_a2a_debug(request.code)

    elapsed = time.perf_counter() - started_at
    fixed_code = get_final_code(steps)

    log_debug_run(request.code, steps, elapsed)

    return {
        "success": is_successful_trace(steps),
        "fixed_code": fixed_code,
        "trace": steps,
    }
