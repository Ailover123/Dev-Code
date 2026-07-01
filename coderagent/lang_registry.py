import json
import re
import subprocess
import shutil
from pathlib import Path

from ddgs import DDGS

from coderagent.settings import get_language_registry_path


BUILTIN_LANGUAGES = {
    "python": {
        "runner": ["python", "-c"],
        "verified": True,
        "source": "builtin",
    },
    "javascript": {
        "runner": ["node", "-e"],
        "verified": True,
        "source": "builtin",
    },
}

LANGUAGE_ALIASES = {
    "py": "python",
    "js": "javascript",
    "node": "javascript",
}

INLINE_RUNNER_PATTERNS = [
    (r"\bpython(?:3)?\s+-c\b", ["python", "-c"], "python"),
    (r"\bnode\s+-e\b", ["node", "-e"], "javascript"),
    (r"\bruby\s+-e\b", ["ruby", "-e"], "ruby"),
    (r"\bphp\s+-r\b", ["php", "-r"], "php"),
    (r"\bperl\s+-e\b", ["perl", "-e"], "perl"),
    (r"\blua\s+-e\b", ["lua", "-e"], "lua"),
    (r"\bdeno\s+eval\b", ["deno", "eval"], "typescript"),
]

FALLBACK_RUNNERS = {
    "python": [["python", "-c"], ["python3", "-c"]],
    "javascript": [["node", "-e"]],
    "php": [["php", "-r"]],
    "ruby": [["ruby", "-e"]],
    "perl": [["perl", "-e"]],
    "lua": [["lua", "-e"]],
    "typescript": [["deno", "eval"], ["node", "-e"]],
}


def get_registry_path() -> Path:
    return get_language_registry_path()


def _normalize_language(language: str) -> str:
    normalized = (language or "auto").lower().strip()
    return LANGUAGE_ALIASES.get(normalized, normalized)


def _load_registry() -> dict:
    path = get_registry_path()

    if not path.exists():
        return dict(BUILTIN_LANGUAGES)

    try:
        with path.open("r", encoding="utf-8") as file:
            stored = json.load(file)
    except (OSError, json.JSONDecodeError):
        stored = {}

    registry = dict(BUILTIN_LANGUAGES)

    for name, entry in stored.items():
        if isinstance(entry, dict) and entry.get("runner"):
            registry[name] = {
                "runner": entry["runner"],
                "verified": bool(entry.get("verified", False)),
                "source": entry.get("source", "learned"),
            }

    return registry


def _save_registry(registry: dict) -> None:
    path = get_registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {}
    for name, entry in registry.items():
        payload[name] = {
            "runner": entry["runner"],
            "verified": bool(entry.get("verified", False)),
            "source": entry.get("source", "learned"),
        }

    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, sort_keys=True)


def _detect_language_from_code(code: str) -> str:
    lowered_code = code.lower()

    python_signals = ["def ", "import ", "print(", "elif ", "except "]
    javascript_signals = ["function ", "const ", "let ", "console.log", "=>"]
    php_signals = ["<?php", "echo ", "fopen(", "fread(", "fclose(", "$file"]
    ruby_signals = ["puts ", "end", "require "]
    perl_signals = ["my $", "use strict", "use warnings"]
    lua_signals = ["print(", "function ", "local "]

    for signal in javascript_signals:
        if signal in lowered_code:
            return "javascript"

    for signal in php_signals:
        if signal in lowered_code:
            return "php"

    for signal in ruby_signals:
        if signal in lowered_code:
            return "ruby"

    for signal in perl_signals:
        if signal in lowered_code:
            return "perl"

    for signal in lua_signals:
        if signal in lowered_code:
            return "lua"

    for signal in python_signals:
        if signal in lowered_code:
            return "python"

    return "unknown"


def _extract_runner_from_text(text: str) -> tuple[list[str], str] | None:
    for pattern, runner, language in INLINE_RUNNER_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return runner, language

    return None


def _verify_runner(runner: list[str]) -> bool:
    if not runner or shutil.which(runner[0]) is None:
        return False

    hello_world_code = {
        "python": "print('hello world')",
        "javascript": "console.log('hello world')",
        "ruby": "puts 'hello world'",
        "php": "echo 'hello world';",
        "perl": "print \"hello world\\n\";",
        "lua": "print('hello world')",
        "typescript": "console.log('hello world')",
    }

    test_code = "print('hello world')"

    if "node" in runner:
        test_code = hello_world_code["javascript"]
    elif "ruby" in runner:
        test_code = hello_world_code["ruby"]
    elif "php" in runner:
        test_code = hello_world_code["php"]
    elif "perl" in runner:
        test_code = hello_world_code["perl"]
    elif "lua" in runner:
        test_code = hello_world_code["lua"]
    elif "deno" in runner:
        test_code = hello_world_code["typescript"]

    try:
        result = subprocess.run(
            [*runner, test_code],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return False

    return result.returncode == 0


def _learn_runner_from_web(code: str, preferred_language: str) -> tuple[list[str], str, bool] | None:
    query_language = preferred_language if preferred_language != "unknown" else "code"
    query = f"run {query_language} code from command line one-liner"

    try:
        results = DDGS().text(query, max_results=5)
    except Exception:
        results = []

    for result in results:
        title = result.get("title", "")
        body = result.get("body", "")
        href = result.get("href", "")
        combined_text = f"{title}\n{body}\n{href}"

        extracted = _extract_runner_from_text(combined_text)
        if extracted:
            runner, language_name = extracted
            verified = _verify_runner(runner)
            return runner, language_name, verified

    for fallback_language in [preferred_language, _detect_language_from_code(code)]:
        for runner in FALLBACK_RUNNERS.get(fallback_language, []):
            if _verify_runner(runner):
                return runner, fallback_language, True

    return None


def list_supported_languages() -> list[dict]:
    registry = _load_registry()
    languages = []

    for name in sorted(registry):
        entry = registry[name]
        languages.append({
            "name": name,
            "runner": " ".join(entry["runner"]),
            "verified": bool(entry.get("verified", False)),
            "source": entry.get("source", "learned"),
        })

    return languages


def resolve_runner(language: str, code: str) -> tuple[list[str], str, bool, str]:
    registry = _load_registry()
    normalized_language = _normalize_language(language)

    explicit_language = normalized_language not in {"auto", "unknown"}

    if normalized_language in registry:
        entry = registry[normalized_language]
        runner = entry["runner"]

        if _verify_runner(runner):
            return runner, normalized_language, True, ""

        return [], normalized_language, False, "Language detected but runner is not available on this machine."

    detected_language = _detect_language_from_code(code)
    if not explicit_language and detected_language in registry:
        entry = registry[detected_language]
        runner = entry["runner"]

        if _verify_runner(runner):
            return runner, detected_language, True, ""

        return [], detected_language, False, "Language detected but runner is not available on this machine."

    learned = _learn_runner_from_web(code, normalized_language)
    if learned:
        runner, learned_language, verified = learned
        registry[learned_language] = {
            "runner": runner,
            "verified": verified,
            "source": "learned",
        }
        _save_registry(registry)

        if verified and _verify_runner(runner):
            return runner, learned_language, True, ""

        return runner, learned_language, False, "Language detected but runner could not be verified on this machine."

    fallback_message = "Language detected but runner could not be verified on this machine."
    if explicit_language:
        for runner in FALLBACK_RUNNERS.get(normalized_language, []):
            if _verify_runner(runner):
                return runner, normalized_language, True, ""

        return [], normalized_language, False, fallback_message

    if normalized_language == "auto" or normalized_language == "unknown":
        if detected_language != "unknown":
            for runner in FALLBACK_RUNNERS.get(detected_language, []):
                if _verify_runner(runner):
                    return runner, detected_language, True, ""

        return [], detected_language if detected_language != "unknown" else "unknown", False, fallback_message

    return [], normalized_language, False, fallback_message
