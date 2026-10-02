"""Small, request-local continuation cache. No disk persistence or approval tokens."""

import threading
import time

from app.task_state import TaskState


class TaskStore:
    def __init__(self, ttl_seconds=900, capacity=16):
        self.ttl_seconds = ttl_seconds
        self.capacity = capacity
        self._items: dict[str, tuple[float, TaskState]] = {}
        self._lock = threading.Lock()

    def put(self, state: TaskState):
        with self._lock:
            now = time.monotonic()
            self._items = {key: item for key, item in self._items.items() if item[0] > now}
            if len(self._items) >= self.capacity:
                oldest = min(self._items, key=lambda key: self._items[key][0])
                del self._items[oldest]
            self._items[state.id] = (now + self.ttl_seconds, state)

    def take(self, task_id: str) -> TaskState:
        with self._lock:
            item = self._items.pop(task_id, None)
            if item is None or item[0] <= time.monotonic():
                raise KeyError('This clarification expired or was already used. Start a new task.')
            return item[1]
