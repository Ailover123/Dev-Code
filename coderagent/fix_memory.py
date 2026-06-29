import chromadb


client = chromadb.PersistentClient(path="coderagent/chroma_db")

collection = client.get_or_create_collection(name="past_fixes")


def save_fix(error: str, broken_code: str, fixed_code: str) -> None:
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
        metadatas=[{"error": error}],
        ids=[str(abs(hash(document)))],
    )


def search_fix_memory(error: str) -> str:
    results = collection.query(
        query_texts=[error],
        n_results=2,
    )

    documents = results["documents"][0]

    if not documents:
        return "No similar past fix found."

    return "\n\n".join(documents)