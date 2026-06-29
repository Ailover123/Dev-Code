from langchain_core.tools import Tool

from coderagent.sandbox import safe_exec


# Splits optional language and code sections from tool input.
def parse_run_input(tool_input: str) -> tuple[str, str]:
    if tool_input.startswith("LANGUAGE:") and "| CODE:" in tool_input:
        language_part, code = tool_input.split("| CODE:", 1)
        language = language_part.replace("LANGUAGE:", "", 1).strip()
        return language, code.strip()

    return "auto", tool_input


# Executes code through the sandbox and formats the result for the agent.
def run_code(code: str) -> str:
    language, code = parse_run_input(code)
    result = safe_exec(code, language)

    if result["success"]:
        return f"SUCCESS\nLanguage: {result['language']}\nOutput:\n{result['output']}"

    return f"FAILED\nLanguage: {result['language']}\nError Type: {result['error_type']}\nError:\n{result['error']}"


RunCodeTool = Tool(
    name="run_code",
    description="Execute Python or JavaScript code and return stdout or stderr. Input is code, or 'LANGUAGE: <language> | CODE: <code>'.",
    func=run_code,
)
