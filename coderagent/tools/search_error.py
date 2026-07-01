from ddgs import DDGS
from langchain_core.tools import Tool


def _parse_search_input(search_input: str) -> tuple[str, str, str]:
    language = ""
    error = search_input
    code = ""

    if "| ERROR:" not in search_input:
        return language, error, code

    leading_part, remainder = search_input.split("| ERROR:", 1)
    error = remainder

    if leading_part.startswith("LANGUAGE:"):
        language_part = leading_part.replace("LANGUAGE:", "", 1)

        if "| CODE:" in language_part:
            language, code = language_part.split("| CODE:", 1)
        else:
            language = language_part

    if "| CODE:" in error:
        error, code = error.split("| CODE:", 1)

    return language.strip(), error.strip(), code.strip()


def _extract_keywords(text: str, limit: int = 12) -> list[str]:
    words = []

    for token in text.replace("\n", " ").replace("\r", " ").split():
        cleaned = "".join(character for character in token if character.isalnum() or character in {"_", "-", "+"})

        if len(cleaned) >= 4:
            words.append(cleaned)

    return words[:limit]


def _build_query(language: str, error: str, code: str) -> str:
    lowered_error = error.lower()
    code_keywords = " ".join(_extract_keywords(code))

    if "unsupportedlanguageerror" in lowered_error or "runner could not be verified" in lowered_error:
        if language:
            return f"how to run {language} code from command line {code_keywords}".strip()

        return f"how to run code from command line {code_keywords}".strip()

    language_part = f"{language} " if language else ""
    return f"{language_part}{error} {code_keywords}".strip()


# Searches the web for explanations and fixes for a Python error message.
def search_error(error: str) -> str:
    language, parsed_error, code = _parse_search_input(error)
    query = _build_query(language, parsed_error, code)

    results = DDGS().text(query, max_results=5)

    snippets = []

    for result in results:
        title = result.get("title", "")
        body = result.get("body", "")
        href = result.get("href", "")

        snippets.append(f"{title}\n{body}\n{href}")

    if not snippets:
        return "No search results found."

    header = [f"Query Used: {query}"]

    if language:
        header.append(f"Language: {language}")

    return "\n".join(header + ["", *snippets])


SearchErrorTool = Tool(
    name="search_error",
    description="Search for explanations and fixes for a Python error message. Input is the error string.",
    func=search_error,
)