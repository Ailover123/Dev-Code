# Turns a failed code execution result into a short analysis message.
def analyze_error(error_result: str) -> str:
    if "Error Type:" not in error_result:
        return "AnalyzerAgent: No clear Python error type was found."

    for line in error_result.splitlines():
        if line.startswith("Error Type:"):
            error_type = line.replace("Error Type:", "").strip()
            return f"AnalyzerAgent: The code failed with {error_type}."

    return "AnalyzerAgent: The code failed, but the error type is unclear."