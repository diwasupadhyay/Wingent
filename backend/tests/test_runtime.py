import asyncio
import time

import pytest

from app.runtime import AgentRuntime
from app.task_state import Action, BudgetExceeded, Decision, Evidence, Limits, Outcome, TaskState, TaskStatus, Verification


class World:
    def __init__(self):
        self.value = 0
        self.actions = []

    async def observe(self, state):
        return {'value': self.value}

    async def validate(self, action):
        assert action.tool == 'increment'

    async def execute(self, action):
        self.actions.append(action)
        self.value += action.arguments['amount']
        return Outcome(status='accepted', summary='Accepted')

    async def verify(self, state, observation):
        if observation.facts['value'] == 3:
            return Verification(evidence=[Evidence(criterion='value=3', observation_id=observation.id, detail='Read value 3')])
        return Verification()

    async def decide(self, context):
        value = context['observations'][-1]['facts']['value']
        return Decision(kind='act', action=Action(tool='increment', arguments={'amount': 1 if value == 0 else 2}, label='Increment'))


def run(world, state=None, disconnected=None):
    state = state or TaskState(goal='Reach three', criteria=['value=3'])
    async def connected():
        return False
    async def collect():
        return [event async for event in AgentRuntime(state, world, world, world, world, disconnected or connected).run()]
    return state, asyncio.run(collect())


def test_reasons_from_changed_observation_and_verifies_goal():
    world = World()
    state, events = run(world)
    assert [a.arguments['amount'] for a in world.actions] == [1, 2]
    assert state.status == TaskStatus.COMPLETED
    assert events[-1][1]['verified'] is True
    assert len(state.evidence) == 1


def test_model_finish_without_evidence_is_not_success():
    class Finish(World):
        async def decide(self, context):
            return Decision(kind='finish', message='I did it all!')
    state, events = run(Finish())
    assert state.status == TaskStatus.UNVERIFIED
    assert events[-1][1]['verified'] is False


def test_stale_or_unrelated_evidence_is_rejected():
    state = TaskState(goal='Reach three', criteria=['value=3'])
    old = state.observe({'value': 3})
    current = state.observe({'value': 0})
    report = Verification(evidence=[Evidence(criterion='value=3', observation_id=old.id, detail='Old')])
    assert not state.verified_by(report, current)
    assert not state.verified_by(report, old)


def test_failure_with_unknown_effect_stops_without_retry():
    class Failed(World):
        async def execute(self, action):
            self.actions.append(action)
            raise RuntimeError('Lost connection after dispatch')
    world = Failed()
    state, events = run(world)
    assert len(world.actions) == 1
    assert state.records[-1].outcome.status == 'unknown'
    assert events[-1][1]['code'] == 'partial_execution'


def test_known_no_effect_can_replan_and_recover():
    class Recover(World):
        async def execute(self, action):
            if not self.actions:
                self.actions.append(action)
                self.value = 1  # External state changed, but this action did not apply.
                return Outcome(status='no_effect', summary='Target changed before invocation')
            return await super().execute(action)
    state, _ = run(Recover())
    assert state.status == TaskStatus.COMPLETED
    assert state.recoveries == 1


def test_cancellation_between_actions():
    world = World()
    async def disconnected():
        return len(world.actions) > 0
    state, _ = run(world, disconnected=disconnected)
    assert len(world.actions) == 1
    assert state.status == TaskStatus.CANCELLED


def test_action_budget_is_enforced():
    state, events = run(World(), TaskState(goal='Reach three', criteria=['value=3'], limits=Limits(actions=1)))
    assert state.status == TaskStatus.FAILED
    assert len(state.records) == 1
    assert 'budget' in events[-1][1]['message']


def test_compact_observation_history():
    state = TaskState(goal='Inspect', criteria=['observed'])
    for _ in range(100):
        state.observe({'content': 'x' * 10000})
    assert len(state.observations) == 4
    assert len(str(state.context())) < 5000


def test_accepted_action_is_never_automatically_repeated():
    class Repeat(World):
        async def decide(self, context):
            return Decision(kind='act', action=Action(tool='increment', arguments={'amount': 1}, label='Increment'))
    world = Repeat()
    state, events = run(world)
    assert len(world.actions) == 1
    assert state.status == TaskStatus.AWAITING_INPUT
    assert events[-1][0] == 'clarification'


def test_recovery_budget_stops_known_failures():
    class Rejected(World):
        async def validate(self, action):
            raise ValueError('Target missing')
    state, events = run(Rejected(), TaskState(goal='Reach three', criteria=['value=3'], limits=Limits(recoveries=1)))
    assert state.status == TaskStatus.FAILED
    assert state.recoveries == 1
    assert all(not record.dispatched for record in state.records)
    assert 'Recovery budget' in events[-1][1]['message']


def test_slow_reasoning_refreshes_unchanged_state_without_infinite_replanning():
    class SlowPlanner(World):
        async def decide(self, context):
            await asyncio.sleep(0.02)
            return await super().decide(context)
    state, _ = run(SlowPlanner(), TaskState(goal='Reach three', criteria=['value=3'],
        limits=Limits(decisions=2, observation_max_age=0.005)))
    assert state.status == TaskStatus.COMPLETED
    assert state.decisions == 2
    assert len(state.records) == 2


def test_changed_state_after_slow_reasoning_cannot_dispatch_stale_action():
    class Changing(World):
        async def observe(self, state):
            self.value += 1
            return {'value': self.value}

        async def decide(self, context):
            await asyncio.sleep(0.02)
            return await super().decide(context)

        async def verify(self, state, observation):
            return Verification()
    state, _ = run(Changing(), TaskState(goal='Reach three', criteria=['value=3'],
        limits=Limits(decisions=2, observation_max_age=0.005)))
    assert state.status == TaskStatus.FAILED
    assert not state.records


def test_pending_observation_is_cancelled_on_timeout():
    cleanup = []
    class Stuck(World):
        async def observe(self, state):
            try:
                await asyncio.Event().wait()
            finally:
                cleanup.append(True)
    state, events = run(Stuck(), TaskState(goal='Inspect', criteria=['observed'], limits=Limits(operation_seconds=0.02)))
    assert state.status == TaskStatus.FAILED
    assert cleanup == [True]
    assert 'No actions were dispatched' in events[-1][1]['message']


def test_cancel_in_flight_marks_unknown_and_prevents_next_action():
    world = World()
    started = False
    cancelled = []
    async def execute(action):
        nonlocal started
        started = True
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)
    world.execute = execute
    async def disconnected():
        return started
    state, _ = run(world, disconnected=disconnected)
    assert state.status == TaskStatus.CANCELLED
    assert len(state.records) == 1
    assert state.records[0].outcome.status == 'unknown'
    assert cancelled == [True]


def test_verification_requires_all_criteria_from_current_observation():
    state = TaskState(goal='Two results', criteria=['first', 'second'])
    current = state.observe({'first': True})
    report = Verification(evidence=[Evidence(criterion='first', observation_id=current.id, detail='Observed')])
    assert not state.verified_by(report, current)


def test_expired_evidence_rejected():
    state = TaskState(goal='Reach three', criteria=['value=3'])
    current = state.observe({'value': 3})
    current.captured_at = time.monotonic() - 60
    report = Verification(evidence=[Evidence(criterion='value=3', observation_id=current.id, detail='Observed')])
    assert not state.verified_by(report, current)


def test_verifier_exception_after_dispatch_preserves_partial_outcome():
    class BrokenVerifier(World):
        async def verify(self, state, observation):
            if state.records:
                raise RuntimeError('Observer failed')
            return Verification()
    state, events = run(BrokenVerifier())
    assert len(state.records) == 1
    assert events[-1][1]['code'] == 'partial_execution'
    assert 'No actions' not in events[-1][1]['message']


def test_unsupported_goal_requests_user_input_without_execution():
    class Unsupported(World):
        async def decide(self, context):
            return Decision(kind='ask', message='This capability is not installed yet.')
    state, _ = run(Unsupported())
    assert state.status == TaskStatus.AWAITING_INPUT
    assert not state.records
    assert state.pending_question


def test_budgeted_provider_counts_each_generation_including_repairs():
    from app.launch_runtime import BudgetedProvider
    from app.planner import plan_request
    calls = []
    class Invalid:
        async def structured(self, *args):
            calls.append(args)
            return 'not json'
    state = TaskState(goal='Task', criteria=['done'], limits=Limits(model_calls=1))
    provider = BudgetedProvider(Invalid(), state)
    with pytest.raises(BudgetExceeded):
        asyncio.run(plan_request('Task', provider))
    assert len(calls) == 1
    assert state.model_calls == 1


def test_total_time_budget_includes_initial_planning():
    state = TaskState(goal='Task', criteria=['done'], started_at=time.monotonic() - 200)
    world = World()
    state, _ = run(world, state)
    assert state.status == TaskStatus.FAILED
    assert not world.actions


def test_invalid_tool_result_after_dispatch_is_unknown_not_no_effect():
    class BadResult(World):
        async def execute(self, action):
            return {'unexpected': 'result'}
    state, events = run(BadResult())
    assert state.records[0].dispatched
    assert state.records[0].outcome.status == 'unknown'
    assert events[-1][1]['code'] == 'partial_execution'


def test_closing_stream_after_terminal_event_preserves_terminal_state():
    world = World()
    state = TaskState(goal='Reach three', criteria=['value=3'])
    async def connected():
        return False
    async def consume():
        stream = AgentRuntime(state, world, world, world, world, connected).run()
        async for event, payload in stream:
            if event == 'final':
                await stream.aclose()
                break
    asyncio.run(consume())
    assert state.status == TaskStatus.COMPLETED
