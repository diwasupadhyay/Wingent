"""Opt-in local Ollama evaluation. Produces plans ONLY; never executes tools.

Run: $env:PYTHONPATH='backend'; python scripts/evaluate-planner.py
"""
import asyncio
import time

from app.llm import OllamaClient
from app.planner import plan_request, compile_plan


CASES = [
    ('can you open chrome and search about genai on youtube and in new tab open github on it',
     'execute', ['youtube.com/results?search_query=genai', 'github.com']),
    ('Please look up generative AI tutorials on YouTube using Edge, then put github.com in another tab',
     'execute', ['youtube.com/results?search_query=', 'github.com']),
    ('I want you to open my Downloads folder and launch Notepad',
     'execute', ['downloads', 'notepad']),
    ('Open Chrome and something else', 'clarify', []),
    ('Open Chrome, go to Gmail, and check whether I have important emails', 'clarify', []),
    ('Open my project folder', 'clarify', []),
    ('What is generative AI?', 'answer', []),
]


async def main():
    failures = []
    for prompt, disposition, targets in CASES:
        started = time.monotonic()
        try:
            plan = await plan_request(prompt, OllamaClient())
            actions = compile_plan(plan)
            actual = [str(params.get('url') or params.get('path') or params.get('application')).lower()
                      for _, params in actions]
            passed = plan.disposition == disposition and len(actual) == len(targets) and all(
                expected in value for expected, value in zip(targets, actual))
            if 'chrome' in prompt.lower() and disposition == 'execute':
                passed &= all(params.get('browser') == 'chrome' for _, params in actions)
            if 'Edge' in prompt and disposition == 'execute':
                passed &= all(params.get('browser') == 'edge' for _, params in actions)
            print(f'{"PASS" if passed else "FAIL"} {time.monotonic() - started:.1f}s: {prompt}', flush=True)
            print(plan.model_dump_json(), flush=True)
            if not passed:
                failures.append(prompt)
        except Exception as exc:
            failures.append(prompt)
            print(f'FAIL: {prompt}: {exc}', flush=True)
    if failures:
        raise SystemExit(f'{len(failures)} evaluation(s) failed. No tools were executed.')
    print(f'{len(CASES)} evaluations passed. No tools were executed.')


if __name__ == '__main__':
    asyncio.run(main())
