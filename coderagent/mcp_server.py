from mcp.server.fastmcp import FastMCP

from coderagent.agents.orchestrator import run_a2a_debug
from coderagent.tools.run_code import run_code
from coderagent.tools.search_error import search_error
from coderagent.tools.search_memory import search_memory


mcp = FastMCP("Dev-Code")


@mcp.tool()
def run_python_code(code: str) -> str:
    """Run Python code safely through CoderAgent's sandbox."""
    return run_code(code)


@mcp.tool()
def search_python_error(error: str) -> str:
    """Search the web for explanations and fixes for a Python error."""
    return search_error(error)


@mcp.tool()
def search_fix_memory(error: str) -> str:
    """Search CoderAgent memory for similar past bug fixes."""
    return search_memory(error)


@mcp.tool()
def debug_python_code(code: str) -> list[dict]:
    """Debug broken Python code using the A2A CoderAgent workflow."""
    return run_a2a_debug(code)


if __name__ == "__main__":
    mcp.run()