"""Packaged smoke test: deny a URL launch, approve opening the repository folder once.

Requires the operator-v3 backend. Never prints approval tokens.
"""

import asyncio
import json
from pathlib import Path

import httpx


async def scenario(client, prompt, approve):
    event = ''
    pending = None
    terminal = None
    async with client.stream('POST', '/api/command', json={'prompt': prompt, 'review_actions': True}) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if line.startswith('event:'):
                event = line[6:].strip()
            elif line.startswith('data:'):
                data = json.loads(line[5:].strip())
                if event == 'confirmation_required':
                    assert pending is None, 'Unexpected extra approval'
                    pending = data
                    reply = await client.post(f'/api/approvals/{data["approval_id"]}',
                                              json={'token': data['token'], 'approve': approve})
                    reply.raise_for_status()
                elif event == 'step' and data['state'] == 'running':
                    assert pending is not None and approve, 'Dispatch before approval or after denial'
                elif event in {'final', 'clarification', 'error'}:
                    terminal = (event, data)
    assert pending is not None and terminal is not None
    if approve:
        assert terminal[0] == 'final' and terminal[1]['outcome'] == 'unverified'
        assert len(terminal[1]['completed']) == 1
    else:
        assert terminal[0] == 'clarification' and terminal[1]['attempted'] == 0
    replay = await client.post(f'/api/approvals/{pending["approval_id"]}',
                               json={'token': pending['token'], 'approve': True})
    assert replay.status_code == 409, 'Approval must be single use'
    print('PASS: approval' if approve else 'PASS: denial', 'and replay rejection')


async def main():
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000', timeout=75) as client:
        health = (await client.get('/health')).json()
        assert health.get('runtime') == 'operator-v3', 'Refusing to test an outdated backend'
        await scenario(client, 'open https://example.com', False)
        await scenario(client, f'open "{Path(__file__).resolve().parent.parent}"', True)


if __name__ == '__main__':
    asyncio.run(main())
