import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import Tool

from coderagent.agent_utils import response_to_text


load_dotenv("coderagent/.env")


# Reads the Gemini key from local env vars or Streamlit Cloud secrets.
def get_gemini_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key:
        return api_key

    try:
        import streamlit as st

        return st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        return ""


# Splits the tool input into code and error sections for the LLM prompt.
def parse_fix_input(tool_input: str) -> tuple[str, str,str]:
    memory = "No memory provided."

    if "| MEMORY:" in tool_input:
        tool_input, memory = tool_input.split("| MEMORY:", 1)
        memory = memory.strip()
    if "| ERROR:" not in tool_input:
        return tool_input.strip(), "No error provided.", memory

    code_part, error_part = tool_input.split("| ERROR:", 1)
    code = code_part.replace("CODE:", "", 1).strip()
    error = error_part.strip()

    return code, error, memory

# Removes Markdown code fences so the sandbox receives plain Python code.
def clean_code_output(code: str) -> str:
    cleaned = code.strip()

    if cleaned.startswith("```python"):
        cleaned = cleaned.replace("```python", "", 1)

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "", 1)

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    return cleaned.strip()


# Uses Gemini to generate corrected Python code from broken code and an error.
def suggest_fix(tool_input: str) -> str:
    code, error, memory = parse_fix_input(tool_input)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=get_gemini_api_key(),
        temperature=0,
    )

    prompt = f"""
You are a careful Python debugging expert.

Fix the code in a way that is safe, readable, and explainable in an interview.
Do not make a random value change just to avoid the error.
Prefer guard clauses, validation, or try/except when they match the error.

Code:
{code}

Error:
{error}

Similar Past Fix Memory:
{memory}

Return ONLY the corrected Python code, no explanation.
"""

    response = llm.invoke(prompt)

    return clean_code_output(response_to_text(response.content))


SuggestFixTool = Tool(
    name="suggest_fix",
    description="Given original code and an error, generate corrected Python code. Input format: 'CODE: <code> | ERROR: <error>'",
    func=suggest_fix,
)
