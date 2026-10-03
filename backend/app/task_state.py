"""Application-independent task contracts. Only trusted adapters produce observations/evidence."""

import json
import time
from enum import Enum
from uuid import uuid4
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, protected_namespaces=())


class TaskStatus(str, Enum):
    OBSERVING = 'observing'
    PLANNING = 'planning'
    EXECUTING = 'executing'
    VERIFYING = 'verifying'
    RECOVERING = 'recovering'
    AWAITING_INPUT = 'awaiting_input'
    COMPLETED = 'completed'
    UNVERIFIED = 'unverified'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class Action(StrictModel):
    tool: str = Field(min_length=1, max_length=100)
    arguments: dict[str, JsonValue] = Field(default_factory=dict)
    label: str = Field(min_length=1, max_length=2200)

    def fingerprint(self) -> str:
        return json.dumps([self.tool, self.arguments], sort_keys=True)


class Decision(StrictModel):
    kind: str = Field(pattern='^(act|finish|ask)$')
    action: Action | None = None
    message: str = Field(default='', max_length=1000)

    @model_validator(mode='after')
    def coherent(self):
        if (self.kind == 'act') != (self.action is not None):
            raise ValueError('Only act decisions contain an action.')
        if self.kind == 'ask' and not self.message.strip():
            raise ValueError('An ask decision needs a question or limitation.')
        return self


class Outcome(StrictModel):
    # no_effect is a trusted adapter guarantee, never an inference from an exception.
    status: str = Field(pattern='^(accepted|no_effect|unknown)$')
    summary: str = Field(max_length=2000)
    data: dict[str, JsonValue] = Field(default_factory=dict)


class ActionRecord(StrictModel):
    action: Action
    outcome: Outcome
    dispatched: bool


class Observation(StrictModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    sequence: int
    action_count: int
    captured_at: float = Field(default_factory=time.monotonic)
    facts: dict[str, JsonValue]


class Evidence(StrictModel):
    criterion: str
    observation_id: str
    detail: str = Field(min_length=1, max_length=1000)


class Verification(StrictModel):
    evidence: list[Evidence] = Field(default_factory=list)


class Limits(StrictModel):
    actions: int = Field(default=16, ge=1, le=64)
    decisions: int = Field(default=24, ge=1, le=128)
    model_calls: int = Field(default=6, ge=1, le=20)
    recoveries: int = Field(default=2, ge=0, le=5)
    seconds: float = Field(default=120.0, gt=0, le=600)
    operation_seconds: float = Field(default=60.0, gt=0, le=120)
    observation_max_age: float = Field(default=5.0, gt=0, le=30)


class BudgetExceeded(RuntimeError):
    pass


PlanText = Annotated[str, Field(min_length=1, max_length=300)]


class WorkingPlan(StrictModel):
    """Model interpretation, never permissions or evidence of completion."""
    outcomes: list[PlanText] = Field(default_factory=list, max_length=8)
    constraints: list[PlanText] = Field(default_factory=list, max_length=8)
    output_targets: list[PlanText] = Field(default_factory=list, max_length=8)
    remaining_work: list[PlanText] = Field(default_factory=list, max_length=8)
    questions: list[PlanText] = Field(default_factory=list, max_length=3)
    based_on_records: list[int] = Field(default_factory=list, max_length=64)

    @model_validator(mode='after')
    def bounded_notes(self):
        if sum(len(text) for field in ('outcomes', 'constraints', 'output_targets', 'remaining_work', 'questions')
               for text in getattr(self, field)) > 2400:
            raise ValueError('Keep planning notes under 2400 characters in total.')
        return self


class TaskState(StrictModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    goal: str = Field(min_length=1, max_length=4096)
    criteria: list[str] = Field(min_length=1, max_length=16)
    status: TaskStatus = TaskStatus.OBSERVING
    limits: Limits = Field(default_factory=Limits)
    started_at: float = Field(default_factory=time.monotonic)
    records: list[ActionRecord] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    observation_sequence: int = 0
    decisions: int = 0
    model_calls: int = 0
    recoveries: int = 0
    pending_question: str | None = None
    clarifications: list[dict[str, str]] = Field(default_factory=list, max_length=3)
    evidence: list[Evidence] = Field(default_factory=list)
    working_plan: WorkingPlan | None = None
    plan_revision: int = 0

    def update_plan(self, plan: WorkingPlan):
        if any(index < 1 or index > len(self.records) for index in plan.based_on_records):
            raise ValueError('Plan references an action result that does not exist.')
        if self.working_plan:
            # Preserve earlier requested outcomes/constraints even if a later model
            # response forgets them. Clarifications and the original goal stay visible.
            for field in ('outcomes', 'constraints', 'output_targets'):
                values = list(dict.fromkeys([*getattr(self.working_plan, field), *getattr(plan, field)]))
                if len(values) > 8:
                    raise ValueError('Plan expanded beyond eight entries; reuse the existing outcomes.')
                setattr(plan, field, values)
        self.working_plan = WorkingPlan.model_validate(plan.model_dump())
        self.plan_revision += 1

    def resume(self, answer: str):
        if not self.pending_question or not answer.strip():
            raise ValueError('A pending question and a nonempty answer are required.')
        if len(self.clarifications) >= 3:
            raise ValueError('This task has reached its clarification limit. Start a new task.')
        self.clarifications.append({'question': self.pending_question, 'answer': answer.strip()[:1000]})
        self.pending_question = None
        self.started_at = time.monotonic()
        self.model_calls = 0
        self.decisions = 0
        self.recoveries = 0
        self.evidence = []
        self.status = TaskStatus.OBSERVING

    def remaining_seconds(self) -> float:
        return self.limits.seconds - (time.monotonic() - self.started_at)

    def consume_model_call(self):
        if self.model_calls >= self.limits.model_calls or self.remaining_seconds() <= 0:
            raise BudgetExceeded('Task model-call or time budget exhausted.')
        self.model_calls += 1

    def observe(self, facts: dict[str, JsonValue]) -> Observation:
        self.observation_sequence += 1
        observation = Observation(sequence=self.observation_sequence, action_count=len(self.records), facts=facts)
        self.observations = [*self.observations[-3:], observation]
        return observation

    def context(self) -> dict:
        """Bound external content, recent records and observations; never send full history."""
        def compact(value, max_chars):
            encoded = json.dumps(value, ensure_ascii=True)
            return value if len(encoded) <= max_chars else {'truncated': True, 'excerpt': encoded[:max_chars]}
        return {
            'goal': self.goal, 'criteria': self.criteria,
            'clarifications': self.clarifications,
            'actions_taken': len(self.records), 'recoveries': self.recoveries,
            'recent_actions': [compact(record.model_dump(mode='json'), 1000) for record in self.records[-6:]],
            'observations': [compact(item.model_dump(mode='json'), 2000) for item in self.observations[-2:]],
        }

    def verified_by(self, report: Verification, observation: Observation) -> bool:
        if not self.observations or observation.id != self.observations[-1].id:
            return False
        if observation.action_count != len(self.records):
            return False
        age = time.monotonic() - observation.captured_at
        if age < 0 or age > self.limits.observation_max_age:
            return False
        supported = {item.criterion for item in report.evidence if item.observation_id == observation.id}
        return bool(self.criteria) and set(self.criteria) <= supported
