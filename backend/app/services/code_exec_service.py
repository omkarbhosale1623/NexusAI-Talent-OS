"""NexusAI Talent OS — Sandboxed code execution service.

Runs candidate code against external sandboxes (Piston / Judge0) and a small
built-in problem bank. Network may be unavailable in dev: every external call
is wrapped, never raises, and returns a structured result.
"""
from __future__ import annotations

import base64
import time
from typing import Optional

import httpx

from app.core.config import settings

# ── Built-in problem bank ──────────────────────────────────────────────────
PROBLEM_BANK: list[dict] = [
    {
        "id": "two_sum",
        "title": "Two Sum",
        "prompt": (
            "Read a line of space-separated integers, then a target integer on "
            "the next line. Print the two 0-based indices (space-separated) of the "
            "numbers that add up to the target."
        ),
        "language_default": "python",
        "starter_code": {
            "python": (
                "nums = list(map(int, input().split()))\n"
                "target = int(input())\n"
                "# print two indices summing to target\n"
            ),
            "javascript": (
                "const lines = require('fs').readFileSync(0,'utf8').split('\\n');\n"
                "const nums = lines[0].trim().split(/\\s+/).map(Number);\n"
                "const target = parseInt(lines[1]);\n"
                "// print two indices summing to target\n"
            ),
        },
        "tests": [
            {"stdin": "2 7 11 15\n9\n", "expected_stdout": "0 1"},
            {"stdin": "3 2 4\n6\n", "expected_stdout": "1 2"},
            {"stdin": "3 3\n6\n", "expected_stdout": "0 1"},
        ],
    },
    {
        "id": "fizzbuzz",
        "title": "FizzBuzz",
        "prompt": (
            "Read an integer N. Print numbers 1..N one per line, but 'Fizz' for "
            "multiples of 3, 'Buzz' for multiples of 5, 'FizzBuzz' for both."
        ),
        "language_default": "python",
        "starter_code": {
            "python": "n = int(input())\n# print fizzbuzz 1..n\n",
            "javascript": (
                "const n = parseInt(require('fs').readFileSync(0,'utf8').trim());\n"
                "// print fizzbuzz 1..n\n"
            ),
        },
        "tests": [
            {"stdin": "5\n", "expected_stdout": "1\n2\nFizz\n4\nBuzz"},
            {"stdin": "3\n", "expected_stdout": "1\n2\nFizz"},
            {
                "stdin": "15\n",
                "expected_stdout": (
                    "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz"
                ),
            },
        ],
    },
    {
        "id": "reverse_string",
        "title": "Reverse String",
        "prompt": "Read a line of text and print it reversed.",
        "language_default": "python",
        "starter_code": {
            "python": "s = input()\n# print s reversed\n",
            "javascript": (
                "const s = require('fs').readFileSync(0,'utf8').replace(/\\n$/,'');\n"
                "// print s reversed\n"
            ),
        },
        "tests": [
            {"stdin": "hello\n", "expected_stdout": "olleh"},
            {"stdin": "NexusAI\n", "expected_stdout": "IAsuxeN"},
            {"stdin": "racecar\n", "expected_stdout": "racecar"},
        ],
    },
]

_PROBLEM_INDEX = {p["id"]: p for p in PROBLEM_BANK}

# ── Language maps ──────────────────────────────────────────────────────────
# Piston: (language, version)
PISTON_LANGUAGE_MAP: dict[str, tuple[str, str]] = {
    "python": ("python", "3.10.0"),
    "javascript": ("javascript", "18.15.0"),
    "java": ("java", "15.0.2"),
    "cpp": ("c++", "10.2.0"),
    "go": ("go", "1.16.2"),
}

# Judge0: language -> language_id
JUDGE0_LANGUAGE_MAP: dict[str, int] = {
    "python": 71,      # Python 3.8.1
    "javascript": 63,  # Node.js 12.14.0
    "java": 62,        # Java OpenJDK 13
    "cpp": 54,         # C++ GCC 9.2.0
    "go": 60,          # Go 1.13.5
}

LANGUAGE_MAP = {"piston": PISTON_LANGUAGE_MAP, "judge0": JUDGE0_LANGUAGE_MAP}

_PISTON_FILE_EXT = {
    "python": "main.py",
    "javascript": "main.js",
    "java": "Main.java",
    "cpp": "main.cpp",
    "go": "main.go",
}


# ── Problem bank accessors ─────────────────────────────────────────────────
def get_problem(problem_id: str) -> Optional[dict]:
    return _PROBLEM_INDEX.get(problem_id)


def list_problems() -> list[dict]:
    return [
        {
            "id": p["id"],
            "title": p["title"],
            "prompt": p["prompt"],
            "language_default": p["language_default"],
            "starter_code": p["starter_code"],
        }
        for p in PROBLEM_BANK
    ]


# ── Execution ──────────────────────────────────────────────────────────────
def _error(reason: str, provider: str) -> dict:
    return {
        "stdout": "",
        "stderr": reason,
        "exit_code": -1,
        "runtime_ms": 0,
        "provider": provider,
        "ok": False,
    }


async def _run_piston(language: str, source: str, stdin: str) -> dict:
    lang, version = PISTON_LANGUAGE_MAP.get(language, (language, "*"))
    payload = {
        "language": lang,
        "version": version,
        "files": [{"name": _PISTON_FILE_EXT.get(language, "main"), "content": source}],
        "stdin": stdin,
        "run_timeout": settings.CODE_EXEC_TIMEOUT_S * 1000,
    }
    started = time.perf_counter()
    async with httpx.AsyncClient(timeout=settings.CODE_EXEC_TIMEOUT_S + 5) as client:
        resp = await client.post(f"{settings.PISTON_URL}/execute", json=payload)
        resp.raise_for_status()
        data = resp.json()
    elapsed = int((time.perf_counter() - started) * 1000)
    run = data.get("run", {}) or {}
    compile_out = (data.get("compile", {}) or {}).get("stderr", "")
    return {
        "stdout": run.get("stdout", "") or "",
        "stderr": (compile_out + (run.get("stderr", "") or "")),
        "exit_code": run.get("code", run.get("signal", 0)) or 0,
        "runtime_ms": elapsed,
        "provider": "piston",
        "ok": True,
    }


async def _run_judge0(language: str, source: str, stdin: str) -> dict:
    lang_id = JUDGE0_LANGUAGE_MAP.get(language)
    if lang_id is None:
        return _error(f"unsupported language for judge0: {language}", "judge0")
    headers = {"Content-Type": "application/json"}
    if settings.JUDGE0_API_KEY:
        headers["X-RapidAPI-Key"] = settings.JUDGE0_API_KEY
    payload = {
        "language_id": lang_id,
        "source_code": base64.b64encode(source.encode()).decode(),
        "stdin": base64.b64encode(stdin.encode()).decode(),
    }
    started = time.perf_counter()
    async with httpx.AsyncClient(timeout=settings.CODE_EXEC_TIMEOUT_S + 5) as client:
        resp = await client.post(
            f"{settings.JUDGE0_URL}/submissions",
            params={"base64_encoded": "true", "wait": "true"},
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
    elapsed = int((time.perf_counter() - started) * 1000)

    def _dec(v: Optional[str]) -> str:
        if not v:
            return ""
        try:
            return base64.b64decode(v).decode(errors="replace")
        except Exception:
            return v

    stderr = _dec(data.get("stderr")) + _dec(data.get("compile_output"))
    return {
        "stdout": _dec(data.get("stdout")),
        "stderr": stderr,
        "exit_code": data.get("exit_code") or 0,
        "runtime_ms": elapsed,
        "provider": "judge0",
        "ok": True,
    }


async def run_code(language: str, source: str, stdin: str = "") -> dict:
    """Execute `source` in `language` with `stdin`. Never raises."""
    provider = settings.CODE_EXEC_PROVIDER
    if not settings.FEATURE_CODING:
        return _error("coding feature disabled", provider)
    if provider == "none":
        return _error("code execution provider disabled (none)", "none")
    try:
        if provider == "piston":
            return await _run_piston(language, source, stdin)
        if provider == "judge0":
            if not settings.JUDGE0_URL:
                return _error("JUDGE0_URL not configured", "judge0")
            return await _run_judge0(language, source, stdin)
        return _error(f"unknown provider: {provider}", provider)
    except httpx.HTTPStatusError as e:
        return _error(f"exec http {e.response.status_code}: {e.response.text[:200]}", provider)
    except (httpx.HTTPError, OSError) as e:
        return _error(f"exec network error: {e}", provider)
    except Exception as e:  # noqa: BLE001 — never crash on exec
        return _error(f"exec error: {e}", provider)


async def run_tests(language: str, source: str, problem_id: str) -> dict:
    """Run `source` against all test cases of `problem_id`."""
    problem = get_problem(problem_id)
    if problem is None:
        return {
            "tests_passed": 0,
            "tests_total": 0,
            "cases": [],
            "score": 0.0,
            "error": f"unknown problem: {problem_id}",
        }
    tests = problem.get("tests", [])
    total = len(tests)
    cases: list[dict] = []
    passed = 0
    for t in tests:
        result = await run_code(language, source, t.get("stdin", ""))
        got = (result.get("stdout") or "").strip()
        expected = (t.get("expected_stdout") or "").strip()
        ok = result.get("ok") and got == expected
        if ok:
            passed += 1
        cases.append(
            {
                "passed": bool(ok),
                "expected": expected,
                "got": got,
                "stderr": result.get("stderr", ""),
            }
        )
    score = round(passed / total * 100, 2) if total else 0.0
    return {
        "tests_passed": passed,
        "tests_total": total,
        "cases": cases,
        "score": score,
    }
