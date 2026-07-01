from coderagent.tools.suggest_fix import SuggestFixTool


def generate_fix(
    broken_code: str,
    error_result: str,
    memory_result: str,
    web_result: str,
    language: str = "auto",
    user_goal: str = "",
) -> str:
    fix_input = (
        f"LANGUAGE: {language}"
        f" | CODE: {broken_code}"
        f" | ERROR: {error_result}"
        f" | MEMORY: {memory_result}"
        f" | WEB: {web_result}"
        f" | USER_GOAL: {user_goal.strip()}"
    )

    return SuggestFixTool.invoke(fix_input)
