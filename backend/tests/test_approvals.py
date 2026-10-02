import time

import pytest

from app.approvals import ApprovalStore


def test_approval_is_single_use():
    store = ApprovalStore()
    item = store.request('task', 'tool', 'v1', {'path': 'a'})
    store.respond(item.id, item.token, True)
    store.consume(item.id, 'task', 'tool', 'v1', {'path': 'a'})
    with pytest.raises(PermissionError):
        store.consume(item.id, 'task', 'tool', 'v1', {'path': 'a'})


@pytest.mark.parametrize('task,tool,revision,args', [
    ('other', 'tool', 'v1', {'path': 'a'}), ('task', 'other', 'v1', {'path': 'a'}),
    ('task', 'tool', 'v2', {'path': 'a'}), ('task', 'tool', 'v1', {'path': 'b'}),
])
def test_approval_binds_every_action_property(task, tool, revision, args):
    store = ApprovalStore()
    item = store.request('task', 'tool', 'v1', {'path': 'a'})
    store.respond(item.id, item.token, True)
    with pytest.raises(PermissionError):
        store.consume(item.id, task, tool, revision, args)


@pytest.mark.parametrize('reason', ['denied', 'expired', 'cancelled', 'unanswered'])
def test_unapproved_actions_never_run(reason):
    store = ApprovalStore()
    item = store.request('task', 'tool', 'v1', {})
    if reason == 'denied':
        store.respond(item.id, item.token, False)
    elif reason == 'expired':
        item.expires = time.monotonic() - 1
    elif reason == 'cancelled':
        store.revoke_task('task')
    with pytest.raises(PermissionError):
        store.consume(item.id, 'task', 'tool', 'v1', {})


def test_wrong_token_cannot_approve_and_second_response_is_rejected():
    store = ApprovalStore()
    item = store.request('task', 'tool', 'v1', {})
    with pytest.raises(PermissionError):
        store.respond(item.id, 'fake', True)
    store.respond(item.id, item.token, True)
    with pytest.raises(PermissionError):
        store.respond(item.id, item.token, False)
