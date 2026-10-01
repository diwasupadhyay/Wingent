"""Validated sequential execution with explicit outcomes and no automatic side-effect retry."""

import asyncio
from contextlib import suppress
from typing import Awaitable, Callable

from app.tools import ToolRegistry


async def while_connected(operation: Awaitable, disconnected: Callable):
    task = asyncio.create_task(operation)
    try:
        while not task.done():
            if await disconnected():
                raise asyncio.CancelledError
            await asyncio.wait({task}, timeout=0.1)
        return await task
    finally:
        if not task.done():
            task.cancel()
        with suppress(asyncio.CancelledError):
            await task


def step_label(name, params):
    target = params.get('url') or params.get('path') or params.get('application')
    browser = f' in {params["browser"].title()}' if params.get('browser') else ''
    return f'Open {target}{browser}'


async def execute_plan(actions, registry: ToolRegistry, disconnected):
    # Validate the entire plan first. A bad final step cannot cause an earlier launch.
    try:
        checked = [(name, registry.validate(name, params)) for name, params in actions]
    except (ValueError, KeyError, PermissionError, OSError) as exc:
        yield 'error', {'message': f'{exc} No actions were taken.', 'code': 'invalid_plan'}
        return
    labels = [step_label(name, params) for name, params in checked]
    yield 'plan', {'steps': labels}
    completed = []
    for index, (name, params) in enumerate(checked):
        if await disconnected():
            return
        yield 'step', {'index': index, 'state': 'running'}
        yield 'status', {'stage': 'tool_running', 'message': f'Step {index + 1}/{len(checked)}: {labels[index]}'}
        try:
            result = registry.execute(name, params)
            if not result.get('ok'):
                raise RuntimeError('The tool did not accept the request.')
        except Exception as exc:
            yield 'step', {'index': index, 'state': 'failed'}
            yield 'error', {
                'message': f'Step {index + 1} failed: {exc} {len(completed)} earlier step(s) accepted; remaining steps not run.',
                # A retry would duplicate accepted actions (and a failing launcher may have started).
                'code': 'partial_execution', 'completed': completed,
            }
            return
        completed.append(result)
        yield 'step', {'index': index, 'state': 'accepted'}
    yield 'final', {
        'text': f'{len(completed)} launch request(s) accepted. Page contents and window state are not verified.',
        'tool': completed,
    }
