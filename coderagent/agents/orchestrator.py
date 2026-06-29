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

# Adds one visible step to the agent trace.
def add_step(steps: list[dict], step_type: str, agent: str, content: str) -> None:
    steps.append({
        "type": step_type,
        "agent": agent,
        "content": content,
    })


# Runs the A2A debugging workflow by coordinating specialist agents.
def run_a2a_debug(broken_code: str, language: str = "auto") -> list[dict]:
    steps = []

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

    memory_result = run_tool("search_memory", first_result)

    add_step(
        steps,
        "observation",
        "OrchestratorAgent",
        memory_result,
    )

    memory_fixed_code = extract_fixed_code_from_memory(memory_result)
    original_error_type = extract_error_type(first_result)
    memory_error_type = extract_error_type(memory_result)

    memory_matches_error = original_error_type and original_error_type == memory_error_type

    if memory_fixed_code and memory_matches_error:

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
              "Memory returned a fix for a different error type, so I should ignore it.",
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

    search_result = run_tool("search_error", first_result)

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

    fixed_code = generate_fix(broken_code, first_result, memory_result, language)

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
    else:
        add_step(
            steps,
            "final",
            "OrchestratorAgent",
            "The generated fix failed verification.",
        )

    return steps
