import chromadb

from coderagent.sandbox import detect_language
from coderagent.settings import get_chroma_dir


client = chromadb.PersistentClient(path=str(get_chroma_dir()))

collection = client.get_or_create_collection(name="past_fixes")


def save_fix(error: str, broken_code: str, fixed_code: str) -> None:
    language = detect_language(broken_code, "auto")
    error_type = ""

    for line in error.splitlines():
        if line.startswith("Error Type:"):
            error_type = line.replace("Error Type:", "", 1).strip()
            break

    document = f"""
Error:
{error}

Broken Code:
{broken_code}

Fixed Code:
{fixed_code}
"""

    collection.add(
        documents=[document],
        metadatas=[{"error": error, "language": language, "error_type": error_type}],
        ids=[str(abs(hash(document)))],
    )


def _parse_memory_input(error: str) -> tuple[str, str, str]:
    language = ""
    code = ""
    parsed_error = error.strip()

    if error.startswith("LANGUAGE:") and "| ERROR:" in error:
        language_part, remainder = error.split("| ERROR:", 1)
        language = language_part.replace("LANGUAGE:", "", 1).strip()

        if "| CODE:" in remainder:
            parsed_error, code = remainder.split("| CODE:", 1)
        else:
            parsed_error = remainder

        return language.strip(), parsed_error.strip(), code.strip()

    if "Language:" in error and "Error Type:" in error:
        for line in error.splitlines():
            if line.startswith("Language:"):
                language = line.replace("Language:", "", 1).strip()

        return language, error.strip(), code

    return language, parsed_error, code


def search_fix_memory(error: str) -> str:
    language, parsed_error, code = _parse_memory_input(error)

    query_texts = [parsed_error]

    if code:
        query_texts.insert(0, f"{parsed_error} {code}")

    if language:
        query_texts.insert(0, f"{language} {parsed_error} {code}")

    results = None

    if language:
        try:
            results = collection.query(
                query_texts=query_texts,
                n_results=3,
                where={"language": language},
            )
        except Exception:
            results = None

        documents = results["documents"][0] if results and results.get("documents") else []

        if not documents:
            return "No similar past fix found."

        return "\n\n".join(dict.fromkeys(documents))

    results = collection.query(
        query_texts=query_texts,
        n_results=3,
    )

    documents = results["documents"][0] if results and results.get("documents") else []

    if not documents:
        return "No similar past fix found."

    return "\n\n".join(dict.fromkeys(documents))
