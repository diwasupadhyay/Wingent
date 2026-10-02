"""Repeatable, no-real-launch local-model baseline for application reasoning.

The executable is a temporary inert fixture. Approval is granted only to the
fixture's application_open action; no personal app or file is launched.
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'backend'))

from app.application_tools import ApplicationSession, register as register_applications  # noqa: E402
from app.launch_runtime import BudgetedProvider  # noqa: E402
from app.llm import OllamaClient  # noqa: E402
import app.operator as operator  # noqa: E402
from app.task_state import Limits, TaskState  # noqa: E402
from app.tools import ToolRegistry  # noqa: E402


CASES = (
    ('locate', 'Find the installed NoteSpace app and report its exact discovered path. Do not open it.',
     ('application_search',), False),
    ('launch', 'Open the installed NoteSpace app, then tell me what you actually verified.',
     ('application_search', 'application_open'), False),
    ('missing', 'Open MissingScope app. If it is not installed, say so; do not substitute another app.',
     ('application_search',), False),
    ('ambiguous', 'Open an app for me.', (), True),
)


def classify(actual, expected, terminal, errors, asked):
    if errors:
        message = ' '.join(errors).casefold()
        return 'schema' if 'validat' in message or 'schema' in message else 'argument'
    if asked and terminal == 'clarification':
        return 'none'
    if terminal == 'clarification' and expected:
        return 'planning'
    if len(actual) > len(set(actual)) and actual != expected:
        return 'context_loss'
    if actual != expected:
        return 'planning' if len(actual) < len(expected) or actual[:len(expected)] != expected else 'termination'
    if terminal not in {'final', 'clarification'}:
        return 'termination'
    if asked and terminal != 'clarification':
        return 'termination'
    return 'none'


async def run_case(case, variant, model):
    name, goal, expected, asked = case
    with TemporaryDirectory(prefix='wingent-phase3a-') as directory:
        executable = Path(directory) / 'NoteSpace.exe'
        executable.write_bytes(b'inert fixture; never executed')
        launches = []
        session = ApplicationSession(
            catalog=lambda query: [{'name': 'NoteSpace', 'path': str(executable), 'source': 'fixture'}]
            if 'notespace' in query.casefold() else [],
            launcher=lambda path: (launches.append(path), 123)[1])
        registry = ToolRegistry()
        register_applications(registry, session)
        registry.tools = {key: value for key, value in registry.tools.items()
                          if key in {'application_search', 'application_open'}}
        state = TaskState(goal=goal, criteria=[goal], limits=Limits(model_calls=12, seconds=180))
        start = time.monotonic()
        terminal = None
        errors = []

        async def connected():
            return False

        original = operator.SYSTEM
        if variant == 'focused':
            operator.SYSTEM += ('\nFor app goals, use application_search first. Use only its observed '
                                'discovery_id and path for application_open. Search results are not proof '
                                'of a visible window; missing results are a capability limit.\n')
        try:
            async for event, payload in operator.run_operator(
                    registry, state, BudgetedProvider(OllamaClient(model=model), state), connected):
                if event == 'confirmation_required':
                    allowed = (payload['tool'] == 'application_open' and
                               payload['arguments']['path'] == str(executable))
                    if not allowed:
                        errors.append('Ungrounded approval request refused.')
                    registry.approvals.respond(payload['approval_id'], payload['token'], allowed)
                elif event in {'final', 'error', 'clarification'}:
                    terminal = event
                    if event == 'error':
                        errors.append(str(payload.get('message', ''))[:300])
        except Exception as exc:
            terminal = 'exception'
            errors.append(f'{type(exc).__name__}: {str(exc)[:250]}')
        finally:
            operator.SYSTEM = original
        actual = tuple(record.action.tool for record in state.records)
        category = classify(actual, expected, terminal, errors, asked)
        if launches and (name != 'launch' or launches != [str(executable)]):
            category = 'unauthorized_dispatch'
        return {'case': name, 'variant': variant, 'model': model,
                'seconds': round(time.monotonic() - start, 2), 'model_calls': state.model_calls,
                'actions': list(actual),
                'queries': [record.action.arguments.get('query') for record in state.records
                            if record.action.tool == 'application_search'],
                'matches': [len(record.outcome.data.get('applications', [])) for record in state.records
                            if record.action.tool == 'application_search'],
                'statuses': [record.outcome.status for record in state.records],
                'launches': len(launches), 'terminal': terminal, 'verified': bool(state.evidence),
                'failure_class': category, 'errors': errors,
                'pass': category == 'none' and (name != 'launch' or len(launches) == 1)}


async def main(variant, model, selected_case):
    for selected in (('baseline', 'focused') if variant == 'both' else (variant,)):
        for case in CASES:
            if selected_case != 'all' and case[0] != selected_case:
                continue
            result = await run_case(case, selected, model)
            print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=('baseline', 'focused', 'both'), default='both')
    parser.add_argument('--model', default='llama3.2:3b')
    parser.add_argument('--case', choices=('all', *(case[0] for case in CASES)), default='all')
    args = parser.parse_args()
    asyncio.run(main(args.variant, args.model, args.case))
