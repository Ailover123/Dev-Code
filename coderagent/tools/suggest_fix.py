import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import Tool


load_dotenv("coderagent/.env")


# Splits the tool input into code and error sections for the LLM prompt.
def parse_fix_input(tool_input: str) -> tuple[str, str]:
    code_part, error_part = tool_input.split("| ERROR:", 1)
    code = code_part.replace("CODE:", "", 1).strip()
    error = error_part.strip()

    return code, error


# Uses Gemini to generate corrected Python code from broken code and an error.
def suggest_fix(tool_input: str) -> str:
    code, error = parse_fix_input(tool_input)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0,
    )

    prompt = f"""
You are a Python debugging expert. Fix this code:

Code:
{code}

Error:
{error}

Return ONLY the corrected Python code, no explanation.
"""

    response = llm.invoke(prompt)

    return response.content.strip()


SuggestFixTool = Tool(
    name="suggest_fix",
    description="Given original code and an error, generate corrected Python code. Input format: 'CODE: <code> | ERROR: <error>'",
    func=suggest_fix,
)