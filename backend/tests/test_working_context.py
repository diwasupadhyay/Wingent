import pytest

from app.capabilities import Arguments
from app.task_state import Action, ActionRecord, Outcome, TaskState, WorkingPlan
from app.tools import ToolPermission, ToolRegistry
from app.working_context import context_results, repeat_problem, source_coverage, with_task_memory


def record(tool='inspect', arguments=None, data=None, status='accepted'):
    return ActionRecord(action=Action(tool=tool, arguments=arguments or {}, label=tool),
                        outcome=Outcome(status=status, summary='Recorded', data=data or {}), dispatched=True)


def test_context_preserves_old_provenance_and_retrieves_without_rerun():
    state = TaskState(goal='Use original source', criteria=['report'])
    state.records = [record(arguments={'n': n}, data={'text': str(n) * 8000}) for n in range(8)]
    shared = ToolRegistry()
    local = with_task_memory(shared, state)
    history, recent = context_results(state)
    assert len(history) == 8 and len(recent) == 6
    assert history[0]['record_id'] == 1 and recent[0]['record_id'] == 3
    assert recent[0]['result']['truncated_in_context'] is True
    assert sum(len(item['result'].get('excerpt', '')) for item in recent) <= 12_000
    assert shared.get_tool('task_read_result') is None
    first = local.execute('task_read_result', {'record_id': 1})
    second = local.execute('task_read_result', {'record_id': 1, 'offset': first['next_offset']})
    assert first['historical'] is True and first['truncated'] is True
    assert len(first['result_json_chunk']) == 4000 and second['offset'] == 4000
    other = with_task_memory(shared, TaskState(goal='Other task', criteria=['other']))
    assert other.execute('task_read_result', {'record_id': 1})['effect'] == 'no_effect'


def test_plan_keeps_outcomes_across_replanning_and_resume_without_verification():
    state = TaskState(goal='Read and produce a report', criteria=['report accurate'])
    state.update_plan(WorkingPlan(outcomes=['Read source', 'Produce report'], constraints=['Keep source'],
                                  remaining_work=['Read source']))
    state.records.append(record())
    state.update_plan(WorkingPlan(outcomes=['Produce report'], remaining_work=['Produce report'], based_on_records=[1]))
    state.pending_question = 'Which output?'
    state.resume('report.md')
    assert state.working_plan.outcomes == ['Read source', 'Produce report']
    assert state.working_plan.constraints == ['Keep source']
    assert state.working_plan.remaining_work == ['Produce report']
    assert state.evidence == []
    with pytest.raises(ValueError, match='does not exist'):
        state.update_plan(WorkingPlan(based_on_records=[42]))


def test_retrieved_json_chunk_is_not_clipped_into_an_unretrievable_recall():
    state = TaskState(goal='Use recorded text', criteria=['read'])
    state.records.append(record(data={'text': '\\' * 9000}))
    registry = with_task_memory(ToolRegistry(), state)
    chunk = registry.execute('task_read_result', {'record_id': 1})
    state.records.append(record('task_read_result', {'record_id': 1, 'offset': 0}, chunk))
    latest = context_results(state)[1][-1]['result']
    assert latest == chunk
    assert 'truncated_in_context' not in latest


def test_source_coverage_requires_contiguous_pages_of_same_version():
    state = TaskState(goal='Read file', criteria=['read'])
    def page(start, end, final=False, version='v1'):
        return record('read_text', {'path': 'C:/input.txt', 'offset': start},
                      {'path': 'C:/input.txt', 'offset': start, 'next_offset': end,
                       'truncated': not final, 'source_version': version})
    state.records = [page(0, 2048), page(4096, 5000, True)]
    assert source_coverage(state)[0]['complete'] is False
    assert source_coverage(state)[0]['next_offset'] == 2048
    state.records.append(page(2048, 4096))
    assert source_coverage(state)[0]['complete'] is True
    state.records.append(page(2048, 3000, True, 'v2'))
    assert source_coverage(state)[0]['complete'] is False
    assert source_coverage(state)[0]['version_changed'] is True


def test_alternating_observation_cycle_needs_explicit_bounded_refresh():
    registry = ToolRegistry()
    for name, safe in [('inspect_a', True), ('inspect_b', True), ('change', False)]:
        registry.register(name, name, ToolPermission.SAFE, {}, lambda p: {'ok': True},
                          input_model=Arguments, retry_safe=safe)
    state = TaskState(goal='Inspect', criteria=['done'])
    state.records = [record('inspect_a'), record('inspect_b')]
    action = state.records[0].action
    assert repeat_problem(state, registry, action)
    assert repeat_problem(state, registry, action, 'Waiting for the external loading state to change') is None
    state.records.append(record('inspect_a'))
    assert repeat_problem(state, registry, action, 'Waiting for the external loading state to change')
    state.records.append(record('change'))
    assert repeat_problem(state, registry, action) is None
