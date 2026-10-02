"""Ephemeral, single-use approvals. Tokens never enter a model prompt or logs."""

import hashlib
import json
import secrets
import threading
import time
from dataclasses import dataclass


def binding(task_id, tool, revision, arguments):
    return hashlib.sha256(json.dumps([task_id, tool, revision, arguments], sort_keys=True).encode()).hexdigest()


@dataclass
class PendingApproval:
    id: str
    token: str
    task_id: str
    binding: str
    expires: float
    decision: bool | None = None


class ApprovalStore:
    def __init__(self, ttl=60.0):
        self.ttl = ttl
        self._pending: dict[str, PendingApproval] = {}
        self._lock = threading.Lock()

    def request(self, task_id, tool, revision, arguments):
        with self._lock:
            now = time.monotonic()
            self._pending = {key: item for key, item in self._pending.items() if item.expires > now}
            if len(self._pending) >= 64:
                raise PermissionError('Too many pending approvals.')
            item = PendingApproval(secrets.token_urlsafe(24), secrets.token_urlsafe(32), task_id,
                                   binding(task_id, tool, revision, arguments), now + self.ttl)
            self._pending[item.id] = item
            return item

    def respond(self, approval_id, token, approve):
        with self._lock:
            item = self._pending.get(approval_id)
            if item is None or not secrets.compare_digest(item.token, token):
                raise PermissionError('Approval not found or token invalid.')
            if item.expires <= time.monotonic() or item.decision is not None:
                raise PermissionError('Approval expired or already answered.')
            item.decision = approve

    def decision(self, approval_id):
        with self._lock:
            item = self._pending.get(approval_id)
            if item is None or item.expires <= time.monotonic():
                raise PermissionError('Approval expired or task cancelled.')
            return item.decision

    def consume(self, approval_id, task_id, tool, revision, arguments):
        with self._lock:
            item = self._pending.pop(approval_id, None)
            if (item is None or item.decision is not True or item.expires <= time.monotonic()
                    or item.binding != binding(task_id, tool, revision, arguments)):
                raise PermissionError('Approval is missing, expired, used, or does not match this exact action.')

    def revoke_task(self, task_id):
        with self._lock:
            self._pending = {key: item for key, item in self._pending.items() if item.task_id != task_id}
