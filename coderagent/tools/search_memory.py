from langchain_core.tools import Tool

from coderagent.fix_memory import search_fix_memory


# Searches past saved fixes before the agent asks Gemini for a new fix.
def search_memory(error: str) -> str:
    return search_fix_memory(error)


SearchMemoryTool = Tool(
    name="search_memory",
    description="Search saved past bug fixes for a similar error. Input is an error message.",
    func=search_memory,
)