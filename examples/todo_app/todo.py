"""A small task manager used as the system under test in the examples and evals."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import IntEnum
from itertools import count


class Priority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class Task:
    id: int
    title: str
    priority: Priority = Priority.MEDIUM
    due: date | None = None
    done: bool = False
    tags: set[str] = field(default_factory=set)


class TaskNotFound(KeyError):
    pass


class TodoList:
    MAX_TITLE = 100

    def __init__(self) -> None:
        self._tasks: dict[int, Task] = {}
        self._ids = count(1)

    def add(self, title: str, priority: Priority = Priority.MEDIUM, due: date | None = None,
            tags: set[str] | None = None) -> Task:
        title = (title or "").strip()
        if not title:
            raise ValueError("title is required")
        if len(title) > self.MAX_TITLE:
            raise ValueError(f"title must be at most {self.MAX_TITLE} characters")
        if any(t.title.lower() == title.lower() and not t.done for t in self._tasks.values()):
            raise ValueError("an open task with this title already exists")
        task = Task(id=next(self._ids), title=title, priority=priority, due=due, tags=set(tags or ()))
        self._tasks[task.id] = task
        return task

    def get(self, task_id: int) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError:
            raise TaskNotFound(task_id) from None

    def complete(self, task_id: int) -> Task:
        task = self.get(task_id)
        task.done = True
        return task

    def reopen(self, task_id: int) -> Task:
        task = self.get(task_id)
        task.done = False
        return task

    def delete(self, task_id: int) -> None:
        self.get(task_id)
        del self._tasks[task_id]

    def list(self, status: str = "all") -> list[Task]:
        if status not in {"all", "open", "done"}:
            raise ValueError("status must be all, open or done")
        tasks = list(self._tasks.values())
        if status == "open":
            tasks = [t for t in tasks if not t.done]
        elif status == "done":
            tasks = [t for t in tasks if t.done]
        return tasks

    def sorted_by_priority(self) -> list[Task]:
        """Highest priority first; ties broken by earliest due date, then id."""
        return sorted(
            self._tasks.values(),
            key=lambda t: (-t.priority, t.due or date.max, t.id),
        )

    def overdue(self, today: date) -> list[Task]:
        return [t for t in self._tasks.values() if t.due and t.due < today and not t.done]

    def search(self, text: str) -> list[Task]:
        q = text.strip().lower()
        if not q:
            return []
        return [t for t in self._tasks.values() if q in t.title.lower()]

    def by_tag(self, tag: str) -> list[Task]:
        return [t for t in self._tasks.values() if tag in t.tags]
