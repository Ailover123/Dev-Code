from coderagent.tools.run_code import RunCodeTool
from coderagent.tools.search_error import SearchErrorTool
from coderagent.tools.suggest_fix import SuggestFixTool


TOOLS = {
    "run_code": RunCodeTool,
    "search_error": SearchErrorTool,
    "suggest_fix": SuggestFixTool,
}


# Calls a named tool and returns its observation text.
def run_tool(action: str, action_input: str) -> str:
    tool = TOOLS.get(action)

    if tool is None:
        return f"Unknown tool: {action}"

    return tool.invoke(action_input)


# Runs the debugging workflow and returns each visible ReAct-style step.
def run_agent(broken_code: str) -> list[dict]:
    steps = []

    steps.append({
        "type": "thought",
        "content": "I should run the original code first to see the real error.",
    })

    steps.append({
        "type": "action",
        "content": f"run_code: {broken_code}",
    })

    first_result = run_tool("run_code", broken_code)

    steps.append({
        "type": "observation",
        "content": first_result,
    })

    if first_result.startswith("SUCCESS"):
        steps.append({
            "type": "final",
            "content": broken_code,
        })
        return steps

    steps.append({
        "type": "thought",
        "content": "The code failed, so I should search the error before suggesting a fix.",
    })

    steps.append({
        "type": "action",
        "content": f"search_error: {first_result}",
    })

    search_result = run_tool("search_error", first_result)

    steps.append({
        "type": "observation",
        "content": search_result,
    })

    fix_input = f"CODE: {broken_code} | ERROR: {first_result}"

    steps.append({
        "type": "thought",
        "content": "Now I can ask AI to suggest a corrected version of the code.",
    })

    steps.append({
        "type": "action",
        "content": f"suggest_fix: {fix_input}",
    })

    fixed_code = run_tool("suggest_fix", fix_input)

    steps.append({
        "type": "observation",
        "content": fixed_code,
    })

    steps.append({
        "type": "thought",
        "content": "I must run the suggested fix to verify it actually works.",
    })

    steps.append({
        "type": "action",
        "content": f"run_code: {fixed_code}",
    })

    final_result = run_tool("run_code", fixed_code)

    steps.append({
        "type": "observation",
        "content": final_result,
    })

    if final_result.startswith("SUCCESS"):
        steps.append({
            "type": "final",
            "content": fixed_code,
        })
    else:
        steps.append({
            "type": "final",
            "content": "The agent suggested a fix, but verification failed.",
        })

    return steps
