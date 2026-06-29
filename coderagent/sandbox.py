import subprocess

from coderagent.errors import CodeTimeoutError, UnsafeCodeError
from coderagent.errors import extract_error_type, format_exception


DANGEROUS_PATTERNS = [
    "import os",
    "import sys",
    "import subprocess",
    "open(",
    "__import__",
    "eval(",
    "exec(",
]


# Runs user Python code safely after blocking obviously dangerous patterns.
def safe_exec(code: str) -> dict:
    for pattern in DANGEROUS_PATTERNS:
        if pattern in code:
            return {
                "success": False,
                "output": "",
                "error": "Blocked: unsafe code detected",
                "error_type": UnsafeCodeError.__name__,
            }

    try:
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired as error:
        return {
            "success": False,
            "output": error.stdout or "",
            "error": "Execution timed out after 5 seconds",
            "error_type": CodeTimeoutError.__name__,
        }
    except Exception as error:
        message = format_exception(error)
        return {
            "success": False,
            "output": "",
            "error": message,
            "error_type": extract_error_type(message),
        }

    return {
        "success": result.returncode == 0,
        "output": result.stdout,
        "error": result.stderr,
        "error_type": extract_error_type(result.stderr) if result.stderr else "",
    }
