"""Existing (deliberately incomplete) test suite for the todo app."""

from datetime import date

import pytest

from todo import Priority, TaskNotFound, TodoList


@pytest.fixture
def todos():
    return TodoList()


def test_add_task_returns_task_with_id(todos):
    task = todos.add("Write report")
    assert task.id == 1
    assert task.title == "Write report"
    assert task.done is False


def test_add_task_with_empty_title_raises(todos):
    with pytest.raises(ValueError):
        todos.add("   ")


def test_complete_task_marks_done(todos):
    task = todos.add("Pay bills")
    todos.complete(task.id)
    assert todos.get(task.id).done is True


def test_delete_task(todos):
    task = todos.add("Old task")
    todos.delete(task.id)
    # Only checks the list is empty; does not check that deleting again raises.
    assert todos.list() == []


def test_list_open_tasks(todos):
    a = todos.add("A")
    todos.add("B")
    todos.complete(a.id)
    assert [t.title for t in todos.list("open")] == ["B"]


def test_sorted_by_priority_high_first(todos):
    todos.add("low", priority=Priority.LOW)
    todos.add("high", priority=Priority.HIGH)
    # Does not cover the tie-breaker on due date.
    assert todos.sorted_by_priority()[0].title == "high"


def test_search_finds_tasks(todos):
    todos.add("Buy milk")
    todos.add("Call mom")
    assert [t.title for t in todos.search("milk")] == ["Buy milk"]


def test_get_unknown_task_raises(todos):
    with pytest.raises(TaskNotFound):
        todos.get(999)


def test_overdue_returns_past_due_open_tasks(todos):
    todos.add("Late", due=date(2024, 1, 1))
    todos.add("Future", due=date(2030, 1, 1))
    assert [t.title for t in todos.overdue(today=date(2025, 1, 1))] == ["Late"]
