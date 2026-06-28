from langchain_core.tools import Tool

from coderagent.sandbox import safe_exec


# Executes Python code through the sandbox and formats the result for the agent.
def run_code(code: str) -> str:
    result = safe_exec(code)

    if result["success"]:
        return f"SUCCESS\nOutput:\n{result['output']}"

    return f"FAILED\nError Type: {result['error_type']}\nError:\n{result['error']}"


RunCodeTool = Tool(
    name="run_code",
    description="Execute Python code and return stdout or stderr. Input is a string of Python code.",
    func=run_code,
)
