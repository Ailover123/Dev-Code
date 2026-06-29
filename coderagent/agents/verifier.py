from coderagent.tools.run_code import RunCodeTool


# Runs code and returns whether it succeeded plus the raw result.
def verify_code(code: str, language: str = "auto") -> tuple[bool, str]:
    tool_input = f"LANGUAGE: {language} | CODE: {code}"
    result = RunCodeTool.invoke(tool_input)

    success = result.startswith("SUCCESS")

    return success, result
