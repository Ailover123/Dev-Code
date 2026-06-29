from coderagent.tools.run_code import RunCodeTool


# Runs code and returns whether it succeeded plus the raw result.
def verify_code(code: str) -> tuple[bool, str]:
    result = RunCodeTool.invoke(code)

    success = result.startswith("SUCCESS")

    return success, result