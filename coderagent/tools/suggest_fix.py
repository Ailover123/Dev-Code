import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import Tool

from coderagent.agent_utils import response_to_text
from coderagent.sandbox import detect_language


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


# Splits the tool input into language, code, error, and memory sections.
def parse_fix_input(tool_input: str) -> tuple[str, str, str, str, str, str]:
    language = "auto"
    code = ""
    error = "No error provided."
    memory = "No memory provided."
    web = "No web context provided."
    user_goal = ""

    if tool_input.startswith("LANGUAGE:") and "| CODE:" in tool_input:
        language_part, tool_input = tool_input.split("| CODE:", 1)
        language = language_part.replace("LANGUAGE:", "", 1).strip()
        tool_input = f"CODE: {tool_input.strip()}"

    if "| USER_GOAL:" in tool_input:
        tool_input, user_goal = tool_input.split("| USER_GOAL:", 1)
        user_goal = user_goal.strip()

    if "| WEB:" in tool_input:
        tool_input, web = tool_input.split("| WEB:", 1)
        web = web.strip()

    if "| MEMORY:" in tool_input:
        tool_input, memory = tool_input.split("| MEMORY:", 1)
        memory = memory.strip()

    if "| ERROR:" in tool_input:
        code_part, error = tool_input.split("| ERROR:", 1)
        code = code_part.replace("CODE:", "", 1).strip()
        error = error.strip()
    else:
        code = tool_input.replace("CODE:", "", 1).strip()

    return language, code, error, memory, web, user_goal


# Removes Markdown code fences so the sandbox receives plain Python code.
def clean_code_output(code: str) -> str:
    cleaned = code.strip()

    if "```" in cleaned:
        blocks = []
        parts = cleaned.split("```")

        for index in range(1, len(parts), 2):
            blocks.append(parts[index].strip())

        if blocks:
            cleaned = blocks[0]

    lines = [line.rstrip() for line in cleaned.splitlines() if line.strip()]

    if lines and lines[0].lower() in {"python", "javascript", "php", "ruby", "perl", "lua", "typescript", "js", "py"}:
        lines = lines[1:]

    if lines and lines[0].lower().startswith(("language:", "code:", "fixed code:")):
        lines = lines[1:]

    cleaned = "\n".join(lines).strip()

    return cleaned.strip()


# Uses Gemini to generate corrected code from broken code and an error.
def suggest_fix(tool_input: str) -> str:
    language, code, error, memory, web, user_goal = parse_fix_input(tool_input)
    language = detect_language(code, language)
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    llm = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=get_gemini_api_key(),
        temperature=0,
    )

    prompt = f"""
You are a careful {language} debugging expert.

Fix the code in a way that is safe, readable, and explainable in an interview.
Do not make a random value change just to avoid the error.
Prefer guard clauses, validation, or try/except when they match the error.

User Request:
{user_goal or "No extra user request."}

Code:
{code}

Error:
{error}

Similar Past Fix Memory:
{memory}

Web Search Context:
{web}

Return ONLY the corrected {language} code, no explanation.
"""

    response = llm.invoke(prompt)

    return clean_code_output(response_to_text(response.content))


SuggestFixTool = Tool(
    name="suggest_fix",
    description="Given original code and an error, generate corrected Python code. Input format: 'CODE: <code> | ERROR: <error>'",
    func=suggest_fix,
)
