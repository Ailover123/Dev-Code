import subprocess
import re

from coderagent.errors import CodeTimeoutError, UnsafeCodeError
from coderagent.errors import extract_error_type, format_exception
from coderagent.lang_registry import resolve_runner


BLOCKED_CODE_PATTERNS = [
    r"\bimport\s+os\b",
    r"\bimport\s+sys\b",
    r"\bimport\s+subprocess\b",
    r"\bopen\s*\(",
    r"__import__",
    r"\beval\s*\(",
    r"\bexec\s*\(",
]


def _is_blocked_code(code: str) -> bool:
    return any(re.search(pattern, code, re.IGNORECASE) for pattern in BLOCKED_CODE_PATTERNS)

def get_runner_args(language: str, code: str) -> list[str]:
    runner_args, _, _, _ = resolve_runner(language, code)

    if runner_args:
        return [*runner_args, code]

    return []


def detect_language(code: str, preferred_language: str = "auto") -> str:
    preferred_language = preferred_language.lower().strip()

    if preferred_language in {"python", "javascript", "php"}:
        return preferred_language

    lowered_code = code.lower()

    python_signals = ["def ", "import ", "print(", "elif ", "except "]
    javascript_signals = ["function ", "const ", "let ", "console.log", "=>"]
    php_signals = ["<?php", "echo ", "fopen(", "fread(", "fclose(", "$file"]

    for signal in javascript_signals:
        if signal in lowered_code:
            return "javascript"

    for signal in php_signals:
        if signal in lowered_code:
            return "php"

    for signal in python_signals:
        if signal in lowered_code:
            return "python"

    return "unknown"

# Runs user code safely after blocking obviously dangerous patterns.
def safe_exec(code: str, language: str = "auto") -> dict:
    if _is_blocked_code(code):
            return {
                "success": False,
                "output": "",
                "error": "Blocked: unsafe code detected",
                "error_type": UnsafeCodeError.__name__,
                "language": detect_language(code, language),
            }
    language = detect_language(code, language)

    runner_args, resolved_language, verified, runner_message = resolve_runner(language, code)

    if not verified and runner_message:
        return {
            "success": False,
            "output": "",
            "error": runner_message,
            "error_type": "UnsupportedLanguageError",
            "language": resolved_language,
        }

    try:
        result = subprocess.run(
            [*runner_args, code],
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
            "language": resolved_language,
        }
    except Exception as error:
        message = format_exception(error)
        return {
            "success": False,
            "output": "",
            "error": message,
            "error_type": extract_error_type(message),
            "language": resolved_language,
        }

    return {
        "success": result.returncode == 0,
        "output": result.stdout,
        "error": result.stderr,
        "error_type": extract_error_type(result.stderr) if result.stderr else "",
        "language": resolved_language,
    }
