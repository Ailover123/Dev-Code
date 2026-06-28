from ddgs import DDGS
from langchain_core.tools import Tool


# Searches the web for explanations and fixes for a Python error message.
def search_error(error: str) -> str:
    results = DDGS().text(error, max_results=3)

    snippets = []

    for result in results:
        title = result.get("title", "")
        body = result.get("body", "")
        href = result.get("href", "")

        snippets.append(f"{title}\n{body}\n{href}")

    if not snippets:
        return "No search results found."

    return "\n\n".join(snippets)


SearchErrorTool = Tool(
    name="search_error",
    description="Search for explanations and fixes for a Python error message. Input is the error string.",
    func=search_error,
)