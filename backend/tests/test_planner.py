import asyncio
import json

import pytest
from pydantic import ValidationError

from app.planner import AgentPlan, compile_plan, plan_request


def example():
    return {'disposition': 'execute', 'message': '', 'steps': [
        {'action': 'search_youtube', 'target': 'genai', 'browser': 'chrome'},
        {'action': 'open_url', 'target': 'https://github.com', 'browser': 'chrome'},
    ]}


def test_multi_step_plan_compiles_site_search_and_separate_tab():
    assert compile_plan(AgentPlan.model_validate(example())) == [
        ('open_url', {'url': 'https://www.youtube.com/results?search_query=genai', 'browser': 'chrome'}),
        ('open_url', {'url': 'https://github.com', 'browser': 'chrome'}),
    ]


@pytest.mark.parametrize('change', [
    {'disposition': 'clarify'}, {'steps': []},
    {'steps': [{'action': 'shell', 'target': 'whoami', 'browser': 'default'}]},
    {'confirmed': True},
    {'steps': example()['steps'] * 5},
])
def test_rejects_untrusted_or_incoherent_plan(change):
    with pytest.raises(ValidationError):
        AgentPlan.model_validate({**example(), **change})


def test_planner_uses_schema_and_validates_response():
    class FakeProvider:
        async def structured(self, prompt, system, schema):
            assert schema['additionalProperties'] is False
            assert 'ENTIRE' in system
            return json.dumps(example())
    assert len(asyncio.run(plan_request('request', FakeProvider())).steps) == 2


def test_redundant_home_page_removed_before_search():
    data = example()
    data['steps'].insert(0, {'action': 'open_url', 'target': 'https://www.youtube.com/', 'browser': 'chrome'})
    assert len(compile_plan(AgentPlan.model_validate(data))) == 2


def test_invalid_plan_has_only_one_repair_attempt():
    calls = []
    class InvalidProvider:
        async def structured(self, *args):
            calls.append(args)
            return '{"disposition":"execute","message":"","steps":[]}'
    with pytest.raises(ValidationError):
        asyncio.run(plan_request('open chrome', InvalidProvider()))
    assert len(calls) == 2
