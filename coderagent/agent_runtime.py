from coderagent.tools.run_code import RunCodeTool
from coderagent.tools.search_error import SearchErrorTool
from coderagent.tools.search_memory import SearchMemoryTool
from coderagent.tools.suggest_fix import SuggestFixTool


TOOLS = {
    "run_code": RunCodeTool,
    "search_error": SearchErrorTool,
    "search_memory": SearchMemoryTool,
    "suggest_fix": SuggestFixTool,
}


# Calls a named tool and returns its observation text.
def run_tool(action: str, action_input: str) -> str:
    tool = TOOLS.get(action)

    if tool is None:
        return f"Unknown tool: {action}"

    return tool.invoke(action_input)


# Pulls the first fixed code block out of a memory search result.
def extract_fixed_code_from_memory(memory_result: str) -> str:
    if "Fixed Code:" not in memory_result:
        return ""

    fixed_part = memory_result.split("Fixed Code:", 1)[1]

    if "\n\nError:" in fixed_part:
        fixed_part = fixed_part.split("\n\nError:", 1)[0]

    return fixed_part.strip()
