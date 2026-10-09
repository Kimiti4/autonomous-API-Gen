# TaskFlow: organize personal and team work.

TaskFlow helps one person or a small team keep on top of the work they do every
day. Tasks live in named lists. Each task carries a title, optional notes, a
status that moves from open to in progress to done, a priority of low, medium or
high, and an optional due date. Everything is reachable from a simple web page
that talks to a small service over plain HTTP using a shared access key.

## Expected behavior

- Creating a task records its title, notes, priority, due date, status, and
  optional list membership, and makes it immediately fetchable.
- Listing tasks returns every task; fetching one task returns exactly that task.
- Marking a task done and later reopening it changes only the status: priority,
  due date, notes, and list membership are retained.
- Deleting a task removes it; a later fetch reports it as unknown.
- A task created without a due date is valid and stores no due date.
- Tasks can belong to a named list; fetching the task shows which list it is in.
- When an access key is configured, requests without it are rejected with a 401
  response; the liveness endpoint at /health stays open and reports ok.
- The browser page lists tasks, creates them, updates their status, and deletes
  them without reloading the page.

## Notes

- Data is per installation; there is no cross-installation sharing.
- The system must remain understandable to a single maintainer.
