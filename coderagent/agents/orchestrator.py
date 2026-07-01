from coderagent.agents.analyzer import analyze_error
from coderagent.agents.fixer import generate_fix
from coderagent.agents.verifier import verify_code
from coderagent.agent_runtime import extract_fixed_code_from_memory, run_tool
from coderagent.fix_memory import save_fix

# Extracts the error type name from a run_code result or memory result.
def extract_error_type(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("Error Type:"):
            return line.replace("Error Type:", "").strip()

    return ""


def extract_language(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("Language:"):
            return line.replace("Language:", "").strip()

    return ""

def memory_matches_current_error(memory_result: str, current_error: str, current_language: str) -> bool:
    if "No similar past fix found." in memory_result:
        return False

    current_error_type = extract_error_type(current_error)
    memory_error_type = extract_error_type(memory_result)
    memory_language = extract_language(memory_result)

    if current_error_type and memory_error_type and current_error_type != memory_error_type:
        return False

    if current_language and memory_language and current_language != memory_language:
        return False

    return "Fixed Code:" in memory_result

def is_runner_unavailable(text: str) -> bool:
    lowered_text = text.lower()

    return (
        "unsupportedlanguageerror" in lowered_text
        or "runner is not available on this machine" in lowered_text
        or "could not be verified on this machine" in lowered_text
    )

# Adds one visible step to the agent trace.
def add_step(steps: list[dict], step_type: str, agent: str, content: str) -> None:
    steps.append({
        "type": step_type,
        "agent": agent,
        "content": content,
    })


# Runs the A2A debugging workflow by coordinating specialist agents.
def run_a2a_debug(broken_code: str, language: str = "auto", user_goal: str = "") -> list[dict]:
    steps = []

    if user_goal.strip():
        add_step(
            steps,
            "thought",
            "OrchestratorAgent",
            f"User requested: {user_goal.strip()}",
        )

    add_step(
        steps,
        "thought",
        "OrchestratorAgent",
        "I should ask the VerifierAgent to run the original code first.",
    )

    add_step(
        steps,
        "action",
        "VerifierAgent",
        f"run_code: {broken_code}",
    )

    first_success, first_result = verify_code(broken_code, language)

    add_step(
        steps,
        "observation",
        "VerifierAgent",
        first_result,
    )

    if first_success:
        add_step(
            steps,
            "final",
            "OrchestratorAgent",
            broken_code,
        )
        return steps

    analysis = analyze_error(first_result)

    resolved_language = extract_language(first_result) or language

    add_step(
        steps,
        "thought",
        "AnalyzerAgent",
        analysis,
    )

    add_step(
        steps,
        "action",
        "OrchestratorAgent",
        "search_memory: checking past fixes before asking Gemini",
    )

    memory_input = f"LANGUAGE: {resolved_language} | ERROR: {first_result} | CODE: {broken_code}"
    memory_result = run_tool("search_memory", memory_input)

    add_step(
        steps,
        "observation",
        "OrchestratorAgent",
        memory_result,
    )

    memory_fixed_code = extract_fixed_code_from_memory(memory_result)

    if memory_fixed_code and memory_matches_current_error(memory_result, first_result, resolved_language):

        add_step(
            steps,
            "thought",
            "VerifierAgent",
            "Memory returned a fix, so I should verify it before using Gemini.",
        )

        add_step(
            steps,
            "action",
            "VerifierAgent",
            f"run_code: {memory_fixed_code}",
        )

        memory_success, memory_verify_result = verify_code(memory_fixed_code, language)

        add_step(
            steps,
            "observation",
            "VerifierAgent",
            memory_verify_result,
        )

        if memory_success:
            add_step(
                steps,
                "final",
                "OrchestratorAgent",
                memory_fixed_code,
            )
            return steps
    elif memory_fixed_code:
        add_step(
            steps,
            "thought",
            "OrchestratorAgent",
            "Memory returned a fix, but it did not match the current error/language closely enough, so I ignored it.",
        )
    add_step(
        steps,
        "thought",
        "OrchestratorAgent",
        "Memory did not produce a verified fix, so I should search web context.",
    )

    add_step(
        steps,
        "action",
        "OrchestratorAgent",
        "search_error: searching web context for the latest error",
    )

    search_input = f"LANGUAGE: {resolved_language} | ERROR: {first_result} | CODE: {broken_code}"

    search_result = run_tool("search_error", search_input)

    add_step(
        steps,
        "observation",
        "OrchestratorAgent",
        search_result,
    )

    add_step(
        steps,
        "thought",
        "FixerAgent",
        "I should generate a corrected version using the error and memory context.",
    )

    fixed_code = generate_fix(broken_code, first_result, memory_result, search_result, language, user_goal)

    add_step(
        steps,
        "observation",
        "FixerAgent",
        fixed_code,
    )

    add_step(
        steps,
        "thought",
        "VerifierAgent",
        "I should run the generated fix to confirm it works.",
    )

    add_step(
        steps,
        "action",
        "VerifierAgent",
        f"run_code: {fixed_code}",
    )

    final_success, final_result = verify_code(fixed_code, language)

    add_step(
        steps,
        "observation",
        "VerifierAgent",
        final_result,
    )

    if final_success:
        save_fix(first_result, broken_code, fixed_code)

        add_step(
            steps,
            "thought",
            "OrchestratorAgent",
            "The generated fix worked, so I saved it to memory.",
        )

        add_step(
            steps,
            "final",
            "OrchestratorAgent",
            fixed_code,
        )
    elif is_runner_unavailable(final_result) or is_runner_unavailable(first_result):
        add_step(
            steps,
            "thought",
            "OrchestratorAgent",
            "The generated fix could not be verified on this machine, so I should return the best available fix anyway.",
        )

        add_step(
            steps,
            "final",
            "OrchestratorAgent",
            fixed_code,
        )
    else:
        add_step(
            steps,
            "final",
            "OrchestratorAgent",
            "The generated fix failed verification.",
        )

    return steps
