import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from coderagent.tools.run_code import RunCodeTool
from coderagent.tools.search_error import SearchErrorTool
from coderagent.tools.suggest_fix import SuggestFixTool


load_dotenv("coderagent/.env")


SYSTEM_PROMPT = """
You are a Python debugging agent. Use tools to fix broken code.

Available tools: run_code, search_error, suggest_fix

You must follow this order:
1. First call run_code with the exact broken code.
2. If run_code fails, call search_error with the error message.
3. Then call suggest_fix using this exact input format:
   CODE: <original broken code> | ERROR: <error message>
4. Then call run_code with the suggested fixed code.
5. Only after run_code returns SUCCESS, provide Final Answer.

Format EVERY tool-use response as:
Thought: <short reason for the next step>
Action: <tool_name>
Action Input: <input to the tool>

After an Observation is shown to you, continue with the next step.

When the code is fixed and verified working, end with:
Thought: The code is now fixed and verified.
Final Answer: <the corrected code>
"""


TOOLS = {
    "run_code": RunCodeTool,
    "search_error": SearchErrorTool,
    "suggest_fix": SuggestFixTool,
}


# Creates the Gemini model used by the manual agent loop.
def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0,
    )

# Converts Gemini response content into plain text for parsing.
def response_to_text(content) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", ""))

        return "\n".join(parts).strip()

    return str(content).strip()


# Extracts one labeled section from the LLM response text.
def extract_section(text: str, label: str) -> str:
    start = text.find(label)

    if start == -1:
        return ""

    start = start + len(label)
    remaining = text[start:]
    next_label_positions = []

    for next_label in ["Thought:", "Action:", "Action Input:", "Final Answer:"]:
        position = remaining.find(next_label)

        if position != -1:
            next_label_positions.append(position)

    if next_label_positions:
        end = min(next_label_positions)
        return remaining[:end].strip()

    return remaining.strip()


# Calls a named tool and returns its observation text.
def run_tool(action: str, action_input: str) -> str:
    tool = TOOLS.get(action)

    if tool is None:
        return f"Unknown tool: {action}"

    return tool.invoke(action_input)


# Runs the manual ReAct loop and returns each visible step.
# Runs the debugging workflow and returns each visible ReAct-style step.
def run_agent(broken_code: str, max_steps: int = 6) -> list[dict]:
    steps = []

    steps.append({
        "type": "thought",
        "content": "I should run the original code first to see the real error.",
    })

    steps.append({
        "type": "action",
        "content": f"run_code: {broken_code}",
    })

    first_result = run_tool("run_code", broken_code)

    steps.append({
        "type": "observation",
        "content": first_result,
    })

    if first_result.startswith("SUCCESS"):
        steps.append({
            "type": "final",
            "content": broken_code,
        })
        return steps

    steps.append({
        "type": "thought",
        "content": "The code failed, so I should search the error before suggesting a fix.",
    })

    steps.append({
        "type": "action",
        "content": f"search_error: {first_result}",
    })

    search_result = run_tool("search_error", first_result)

    steps.append({
        "type": "observation",
        "content": search_result,
    })

    fix_input = f"CODE: {broken_code} | ERROR: {first_result}"

    steps.append({
        "type": "thought",
        "content": "Now I can ask AI to suggest a corrected version of the code.",
    })

    steps.append({
        "type": "action",
        "content": f"suggest_fix: {fix_input}",
    })

    fixed_code = run_tool("suggest_fix", fix_input)

    steps.append({
        "type": "observation",
        "content": fixed_code,
    })

    steps.append({
        "type": "thought",
        "content": "I must run the suggested fix to verify it actually works.",
    })

    steps.append({
        "type": "action",
        "content": f"run_code: {fixed_code}",
    })

    final_result = run_tool("run_code", fixed_code)

    steps.append({
        "type": "observation",
        "content": final_result,
    })

    if final_result.startswith("SUCCESS"):
        steps.append({
            "type": "final",
            "content": fixed_code,
        })
    else:
        steps.append({
            "type": "final",
            "content": "The agent suggested a fix, but verification failed.",
        })

    return steps
    llm = get_llm()
    prompt_history = f"{SYSTEM_PROMPT}\n\nBroken code:\n{broken_code}"
    steps = []
    verified = False  

    for _ in range(max_steps):
        response = llm.invoke(prompt_history)
        message = response_to_text(response.content)

        thought = extract_section(message, "Thought:")
        action = extract_section(message, "Action:")
        action_input = extract_section(message, "Action Input:")
        final_answer = extract_section(message, "Final Answer:")

        if thought:
            steps.append({"type": "thought", "content": thought})

        if final_answer and verified:
            steps.append({"type": "final", "content": final_answer})
            return steps
        if final_answer and not verified:
            message = (
                "Thought : I'll verify the final answer by running the code to ensure it works correctly. \n"
                "Action: run_code\n" \
                f"Action Input: {final_answer}"
            )
            thought = extract_section(message, "Thought:")
            action = extract_section(message, "Action:")
            action_input = extract_section(message, "Action Input:")

        steps.append({"type": "action", "content": f"{action}: {action_input}"})

        observation = run_tool(action, action_input)
        if action == "run_code" and "SUCCESS" in observation:
            verified = True
        steps.append({"type": "observation", "content": observation})

        prompt_history += f"\n\n{message}\nObservation: {observation}"

    steps.append({
        "type": "final",
        "content": "Agent stopped because max steps were reached.",
    })

    return steps