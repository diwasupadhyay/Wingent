import pytest

from app.task_brain import LaunchMemory, CompletionReview
from app.self_operating import parse_operations
import json


def test_split_launch_is_remembered_and_repeated_batch_rejected_before_input():
    memory = LaunchMemory()
    for raw in ['[{"operation":"press","keys":["win","s"]}]',
                '[{"operation":"write","content":"Chrome"}]',
                '[{"operation":"press","keys":["enter"]}]']:
        for action in parse_operations(raw): memory.record(action)
    assert memory.launched == ['chrome']
    repeat = parse_operations('[{"operation":"press","keys":["win"]},'
        '{"operation":"write","content":" Google Chrome "},{"operation":"press","keys":["enter"]}]')
    with pytest.raises(ValueError, match='Already sent a launch'):
        memory.check_batch(repeat)
    assert memory.searching is False
    memory.check_batch(parse_operations('[{"operation":"press","keys":["win","s"]},'
        '{"operation":"write","content":"Notepad"},{"operation":"press","keys":["enter"]}]'))


def test_review_needs_every_outcome_with_evidence():
    review = CompletionReview(goal_complete=True, checks=[
        {'criterion': 1, 'satisfied': True, 'evidence': 'Calculator open'}], remaining=[])
    assert not review.passed(['Calculator open', '144 is displayed'])
    assert review.passed(['Calculator open'])


def test_newline_search_launch_cannot_bypass_memory():
    memory = LaunchMemory()
    actions = parse_operations('[{"operation":"press","keys":["windows","s"]},'
                               '{"operation":"write","content":"Calculator\\n"}]')
    for action in actions:
        memory.record(action)
    with pytest.raises(ValueError, match='Already sent'):
        memory.check_batch(actions)


def test_ascii_uses_real_keys_and_non_ascii_uses_unicode(monkeypatch):
    from vendor.self_operating_computer.operate.utils.operating_system import OperatingSystem
    import pyautogui
    from app import unicode_input
    typed, unicode_units = [], []
    monkeypatch.setattr(pyautogui, 'write', lambda text, **kwargs: typed.append(text))
    monkeypatch.setattr(unicode_input, 'type_code_unit', unicode_units.append)
    desktop = OperatingSystem()
    monkeypatch.setattr(desktop, 'check', lambda: None)
    desktop.write('72*2é')
    assert ''.join(typed) == '72*2'
    assert unicode_units == [ord('é')]


@pytest.mark.parametrize('alias', ['win', 'windows', 'winleft', 'winright'])
@pytest.mark.parametrize('target', ['', 'notepad', 'search'])
def test_notifications_shortcut_requires_its_actual_target(alias, target):
    with pytest.raises(ValueError, match='notifications'):
        parse_operations(json.dumps([{'operation': 'press', 'keys': [alias, 'n'],
                                      'system_target': target}]))


def test_notification_task_can_still_use_correct_shortcut():
    action = parse_operations('[{"operation":"press","keys":["win","n"],"system_target":"notifications"}]')[0]
    assert action.system_target == 'notifications'


def test_unknown_windows_initial_is_not_treated_as_app_launcher():
    with pytest.raises(ValueError, match='Unsupported Windows shortcut'):
        parse_operations('[{"operation":"press","keys":["win","j"]}]')


def test_ordinary_app_shortcuts_are_unaffected():
    assert parse_operations('[{"operation":"press","keys":["ctrl","n"]}]')[0].keys == ['ctrl', 'n']
