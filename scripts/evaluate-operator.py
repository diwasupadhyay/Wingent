"""Real local-model + real file tools; approval is limited to an isolated test folder.

No personal files, web launches, shell commands, or plugin code are authorized here.
Use --endpoint URL to test the rebuilt packaged API instead of source.
"""

import argparse
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx

from app.file_tools import register
from app.launch_runtime import BudgetedProvider
from app.llm import OllamaClient
from app.operator import run_operator
from app.task_state import TaskState, Limits
from app.tools import ToolRegistry


@dataclass(frozen=True)
class Case:
    name: str
    source_name: str
    source_text: str
    output_name: str
    instruction: str
    expected: tuple[str, ...]


CASES = {
    'fruit': Case('fruit', 'measurements.txt', 'Oranges: 12\nPears: 7\n', 'report.md',
                  'accurately lists the two fruit counts', ('oranges', '12', 'pears', '7')),
    'supplies': Case('supplies', 'stock.txt', 'Pencils: 4\nMarkers: 9\n', 'summary.txt',
                     'summarizes the observed stock counts', ('pencils', '4', 'markers', '9')),
}


def permitted(pending, root, output_name):
    assert pending['tool'] in {'list_directory', 'read_text', 'create_text'}, 'Non-file action proposed'
    target = Path(pending['arguments']['path']).resolve()
    assert target == root or root in target.parents, 'Action escaped isolated test directory'
    if pending['tool'] == 'create_text':
        assert target == root / output_name, 'Unexpected write target'


async def main(endpoint=None, variant='fruit'):
    case = CASES[variant]
    with TemporaryDirectory(prefix='wingent-operator-') as directory:
        root = Path(directory).resolve()
        (root / case.source_name).write_text(case.source_text, encoding='utf-8')
        goal = (f'Inspect the directory "{root}". Read the text file you find there. '
                f'Create a new report at "{root / case.output_name}" that {case.instruction}. '
                'Use the observed file content, not invented data. Do not open applications or websites.')
        terminal = None
        calls = []
        if endpoint:
            async with httpx.AsyncClient(base_url=endpoint, timeout=180) as client:
                assert (await client.get('/health')).json()['runtime'] == 'operator-v4'
                event = ''
                async with client.stream('POST', '/api/command', json={'prompt': goal, 'review_actions': True}) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith('event:'):
                            event = line[6:].strip()
                        elif line.startswith('data:'):
                            data = json.loads(line[5:].strip())
                            if event == 'confirmation_required':
                                permitted(data, root, case.output_name)
                                calls.append(data['tool'])
                                reply = await client.post('/api/approvals/' + data['approval_id'],
                                    json={'token': data['token'], 'approve': True})
                                reply.raise_for_status()
                            elif event in {'final', 'error', 'clarification'}:
                                terminal = event, data
        else:
            registry = ToolRegistry()
            register(registry)
            # Remove real launchers from this isolated source evaluation.
            registry.tools = {k: v for k, v in registry.tools.items() if k in {'list_directory', 'read_text', 'create_text'}}
            state = TaskState(goal=goal, criteria=[goal], limits=Limits(model_calls=12, seconds=180.0))
            async def connected():
                return False
            async for event, data in run_operator(registry, state, BudgetedProvider(OllamaClient(), state), connected):
                if event == 'confirmation_required':
                    permitted(data, root, case.output_name)
                    calls.append(data['tool'])
                    registry.approvals.respond(data['approval_id'], data['token'], True)
                elif event in {'final', 'error', 'clarification'}:
                    terminal = event, data
        print('Tools:', ', '.join(calls), flush=True)
        assert terminal and terminal[0] == 'final', terminal
        assert calls[:3] == ['list_directory', 'read_text', 'create_text'], (calls, terminal)
        text = (root / case.output_name).read_text(encoding='utf-8').casefold()
        assert all(value in text for value in case.expected), text
        assert terminal[1]['verified'] is False, 'Do not elevate artifact checks to whole-goal verification'
        print(f'PASS {case.name}: real model discovered, read, and created a content-checked report; no overwrite.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--endpoint')
    parser.add_argument('--variant', choices=CASES, default='fruit')
    args = parser.parse_args()
    asyncio.run(main(args.endpoint, args.variant))
