"""Compatibility entry point and disconnect-aware planning wait."""

import asyncio
from contextlib import suppress
from typing import Awaitable, Callable

from app.tools import ToolRegistry
from app.launch_runtime import run_launches


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


async def execute_plan(actions, registry: ToolRegistry, disconnected, *, state=None, provider=None):
    async for event in run_launches(actions, registry, disconnected, state, provider):
        yield event
