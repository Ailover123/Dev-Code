import re


class DevCodeError(Exception):
    """Base exception for expected Dev-Code failures."""


class UnsafeCodeError(DevCodeError):
    """Raised when submitted code matches a blocked safety pattern."""


class CodeTimeoutError(DevCodeError):
    """Raised when submitted code runs longer than the sandbox limit."""


class ToolExecutionError(DevCodeError):
    """Raised when an agent tool fails unexpectedly."""


# Extracts the final Python exception name from a traceback string.
def extract_error_type(error_text: str) -> str:
    matches = re.findall(
        r"^([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception)):",
        error_text,
        re.MULTILINE,
    )

    if matches:
        return matches[-1]

    if "Blocked: unsafe code detected" in error_text:
        return "UnsafeCodeError"

    if "timed out" in error_text.lower():
        return "TimeoutError"

    return "UnknownError"


# Converts an exception object into a compact error message.
def format_exception(error: Exception) -> str:
    return f"{error.__class__.__name__}: {error}"
