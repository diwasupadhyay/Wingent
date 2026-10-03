import pytest

from app.task_state import TaskState
from app.task_store import TaskStore


def state(goal):
    return TaskState(goal=goal, criteria=[goal], pending_question='Which target?')


def test_continuation_is_single_use_and_expires():
    store = TaskStore(ttl_seconds=900)
    original = state('Inspect target')
    store.put(original)
    assert store.peek(original.id) is original
    assert store.peek(original.id) is original
    assert store.take(original.id) is original
    with pytest.raises(KeyError):
        store.take(original.id)
    with pytest.raises(KeyError):
        store.peek(original.id)
    expired = TaskStore(ttl_seconds=0)
    expired.put(original)
    with pytest.raises(KeyError):
        expired.take(original.id)
    with pytest.raises(KeyError):
        expired.peek(original.id)


def test_capacity_evicts_oldest_pending_continuation():
    store = TaskStore(capacity=1)
    first, second = state('First'), state('Second')
    store.put(first)
    store.put(second)
    with pytest.raises(KeyError):
        store.take(first.id)
    assert store.take(second.id) is second
