import subprocess


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
            }

    result = subprocess.run(
        ["python", "-c", code],
        capture_output=True,
        text=True,
        timeout=5,
    )

    return {
        "success": result.returncode == 0,
        "output": result.stdout,
        "error": result.stderr,
    }