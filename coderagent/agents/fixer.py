from coderagent.tools.suggest_fix import SuggestFixTool


# Asks the fix tool to generate corrected code.
def generate_fix(
    broken_code: str,
    error_result: str,
    memory_result: str,
    language: str = "auto",
    user_goal: str = "",
) -> str:
    fix_input = f"LANGUAGE: {language} | CODE: {broken_code} | ERROR: {error_result} | MEMORY: {memory_result}"

    if user_goal.strip():
        fix_input = f"{fix_input} | USER_GOAL: {user_goal.strip()}"

    return SuggestFixTool.invoke(fix_input)
