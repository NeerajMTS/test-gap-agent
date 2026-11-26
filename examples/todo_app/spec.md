# Todo app: product requirements

## Creating tasks
- Adding a task with a title returns a new task with a unique id that is not done.
- Adding a task with an empty or blank title raises an error.
- Adding a task with a title longer than 100 characters raises an error.
- Adding an open task with the same title as another open task (case-insensitive) raises a duplicate error.

## Updating tasks
- Completing a task marks it as done.
- Reopening a completed task marks it as not done again.
- Deleting a task removes it from the list.
- Deleting a task that does not exist raises a not-found error.
- Getting a task with an unknown id raises a not-found error.

## Listing and finding
- Listing open tasks returns only tasks that are not done.
- Listing with an invalid status filter raises an error.
- Tasks sorted by priority put high priority first.
- Tasks with equal priority are sorted by the earliest due date.
- Overdue returns open tasks whose due date is in the past.
- Completed tasks are never reported as overdue.
- Search finds tasks whose title contains the text, ignoring case.
- Search with blank text returns no tasks.
- Filtering by tag returns only tasks with that tag.
