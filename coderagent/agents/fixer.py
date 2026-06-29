from coderagent.tools.suggest_fix import SuggestFixTool


# Asks the fix tool to generate corrected code.
def generate_fix(broken_code: str, error_result: str, memory_result: str) -> str:
    fix_input = f"CODE: {broken_code} | ERROR: {error_result} | MEMORY: {memory_result}"

    return SuggestFixTool.invoke(fix_input)