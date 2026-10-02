"""Bounded observe/decide/act/verify loop; no browser or application names here."""

import asyncio
import time
from contextlib import suppress
from typing import Awaitable, Callable, Protocol

from app.task_state import (
    Action, ActionRecord, BudgetExceeded, Decision, Observation, Outcome,
    TaskState, TaskStatus, Verification,
)


class Planner(Protocol):
    async def decide(self, context: dict) -> Decision: ...


class Observer(Protocol):
    async def observe(self, state: TaskState) -> dict: ...


class Executor(Protocol):
    async def validate(self, action: Action) -> None: ...
    async def execute(self, action: Action) -> Outcome: ...


class Verifier(Protocol):
    async def verify(self, state: TaskState, observation: Observation) -> Verification: ...


class TaskCancelled(Exception):
    pass


class AgentRuntime:
    def __init__(self, state: TaskState, planner: Planner, observer: Observer,
                 executor: Executor, verifier: Verifier, disconnected: Callable):
        self.state, self.planner, self.observer = state, planner, observer
        self.executor, self.verifier, self.disconnected = executor, verifier, disconnected

    async def checked(self, operation: Callable[[], Awaitable], timeout=None):
        """Bound every operation and cancel pending async work promptly on disconnect."""
        if await self.disconnected():
            raise TaskCancelled
        remaining = min(self.state.remaining_seconds(), self.state.limits.operation_seconds)
        if timeout is not None:
            remaining = min(remaining, timeout)
        if remaining <= 0:
            raise BudgetExceeded('Task time budget exhausted.')
        task = asyncio.create_task(operation())
        try:
            async with asyncio.timeout(remaining):
                while not task.done():
                    if await self.disconnected():
                        raise TaskCancelled
                    await asyncio.wait({task}, timeout=0.05)
                return await task
        finally:
            if not task.done():
                task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    def status(self, status: TaskStatus, message: str):
        self.state.status = status
        return 'status', {'task_id': self.state.id, 'stage': status.value, 'message': message}

    def terminal(self, status: TaskStatus, text: str, code: str | None = None):
        self.state.status = status
        payload = {'task_id': self.state.id, 'outcome': status.value, 'text': text,
                   'verified': status == TaskStatus.COMPLETED,
                   'completed': [r.outcome.data for r in self.state.records if r.outcome.status == 'accepted'],
                   'attempted': len(self.state.records),
                   'evidence': [item.model_dump() for item in self.state.evidence]}
        if status == TaskStatus.AWAITING_INPUT:
            self.state.pending_question = text
            return 'clarification', payload
        if status == TaskStatus.FAILED:
            payload.update(message=text, code=code or 'runtime_failed')
            return 'error', payload
        return 'final', payload

    async def run(self):
        state = self.state
        in_flight: Action | None = None
        try:
            yield 'task', {'task_id': state.id, 'goal': state.goal, 'criteria': state.criteria}
            while True:
                yield self.status(TaskStatus.OBSERVING, 'Checking current tool state')
                facts = await self.checked(lambda: self.observer.observe(state))
                observation = state.observe(facts)
                yield self.status(TaskStatus.VERIFYING, 'Checking evidence against the goal')
                report = await self.checked(lambda: self.verifier.verify(state, observation))
                if state.verified_by(report, observation):
                    state.evidence = report.evidence
                    yield self.terminal(TaskStatus.COMPLETED, 'Goal verified against observed results.')
                    return

                # An uncertain effect cannot be retried or ignored by a model.
                if state.records and state.records[-1].outcome.status == 'unknown':
                    yield self.terminal(TaskStatus.FAILED,
                        'The last action has an unknown outcome: ' + state.records[-1].outcome.summary + ' '
                        'Check its result before submitting another task. '
                        'Remaining actions were not run.', 'partial_execution')
                    return
                if state.decisions >= state.limits.decisions:
                    raise BudgetExceeded('Task decision budget exhausted.')
                yield self.status(TaskStatus.PLANNING, 'Choosing the next action')
                state.decisions += 1
                decision = await self.checked(lambda: self.planner.decide(state.context()))
                if decision.kind == 'ask':
                    yield self.terminal(TaskStatus.AWAITING_INPUT, decision.message)
                    return
                if decision.kind == 'finish':
                    yield self.terminal(TaskStatus.UNVERIFIED,
                        f'{sum(r.outcome.status == "accepted" for r in state.records)} action request(s) accepted. '
                        'Goal not verified: observation tools cannot yet confirm the requested result.')
                    return
                action = decision.action
                assert action is not None
                if len(state.records) >= state.limits.actions:
                    raise BudgetExceeded('Task action budget exhausted.')
                # Accepted actions are never automatically dispatched again.
                if (not getattr(self.executor, 'safe_to_repeat', lambda _: False)(action) and
                        any(r.action.fingerprint() == action.fingerprint() and r.outcome.status != 'no_effect'
                            for r in state.records)):
                    yield self.terminal(TaskStatus.AWAITING_INPUT,
                        'The next action repeats an earlier accepted request. Please check its result before retrying.')
                    return
                index = len(state.records)
                yield 'action', {'task_id': state.id, 'index': index, 'label': action.label}
                try:
                    await self.checked(lambda: self.executor.validate(action))
                except (ValueError, KeyError, PermissionError, OSError) as exc:
                    outcome = Outcome(status='no_effect', summary=str(exc)[:2000])
                    dispatched = False
                else:
                    request_approval = getattr(self.executor, 'request_approval', None)
                    pending = await self.checked(lambda: request_approval(action)) if request_approval else None
                    if pending:
                        yield self.status(TaskStatus.AWAITING_INPUT, 'Waiting for your approval')
                        yield 'confirmation_required', pending
                        try:
                            await self.checked(lambda: self.executor.await_approval(pending))
                        except PermissionError as exc:
                            yield self.terminal(TaskStatus.AWAITING_INPUT, str(exc))
                            return
                        # Approval does not freeze the world. Refresh and revalidate before dispatch.
                        yield self.status(TaskStatus.OBSERVING, 'Approval received; rechecking the target')
                        observation = state.observe(await self.checked(lambda: self.observer.observe(state)))
                        await self.checked(lambda: self.executor.validate(action))
                    # Observe again if model generation/validation took long enough to stale the state.
                    if time.monotonic() - observation.captured_at > state.limits.observation_max_age:
                        yield self.status(TaskStatus.RECOVERING, 'State expired; observing again before acting')
                        fresh = state.observe(await self.checked(lambda: self.observer.observe(state)))
                        # Slow local inference must not force an endless identical generation.
                        # Changed observations require replanning; unchanged facts can proceed
                        # after target validation. No stale target is dispatched.
                        if fresh.facts != observation.facts:
                            continue
                        await self.checked(lambda: self.executor.validate(action))
                        if time.monotonic() - fresh.captured_at > state.limits.observation_max_age:
                            continue
                    yield self.status(TaskStatus.EXECUTING, action.label)
                    yield 'step', {'index': index, 'state': 'running'}
                    in_flight = action
                    try:
                        outcome = Outcome.model_validate(await self.checked(lambda: self.executor.execute(action),
                            timeout=getattr(self.executor, 'timeout_for', lambda _: None)(action)))
                    except (TaskCancelled, asyncio.CancelledError):
                        raise
                    except Exception as exc:
                        outcome = Outcome(status='unknown', summary=str(exc)[:2000] or 'Action timed out.')
                    dispatched = True
                    in_flight = None
                state.records.append(ActionRecord(action=action, outcome=outcome, dispatched=dispatched))
                yield 'step', {'index': index, 'state': {'accepted': 'accepted', 'no_effect': 'failed', 'unknown': 'unknown'}[outcome.status]}
                if outcome.status == 'no_effect':
                    if state.recoveries >= state.limits.recoveries:
                        raise BudgetExceeded('Recovery budget exhausted; last action had no effect.')
                    state.recoveries += 1
                    yield self.status(TaskStatus.RECOVERING, 'Action had no effect; observing before replanning')
        except (TaskCancelled, asyncio.CancelledError, GeneratorExit):
            if in_flight:
                state.records.append(ActionRecord(action=in_flight, dispatched=True,
                    outcome=Outcome(status='unknown', summary='Cancelled during dispatch; action may still finish.')))
            if state.status not in {TaskStatus.COMPLETED, TaskStatus.UNVERIFIED, TaskStatus.FAILED, TaskStatus.AWAITING_INPUT}:
                state.status = TaskStatus.CANCELLED
            # The transport may already be closed; retain state but do not yield from cancellation cleanup.
            return
        except Exception as exc:
            has_effects = any(r.dispatched for r in state.records)
            suffix = ' Earlier action requests may have taken effect.' if has_effects else ' No actions were dispatched.'
            yield self.terminal(TaskStatus.FAILED, (str(exc) or 'Task operation timed out.') + suffix,
                                'partial_execution' if has_effects else 'runtime_failed')
