# ReadingShelf: keep a shared reading queue

ReadingShelf helps a small book club keep track of books members want to read.
It should be a small web application backed by a plain HTTP service and suitable
for one maintainer.

## Expected behavior

- A book has a title, author, reading state, and optional notes.
- Members can add a book, list all books, fetch one book, update its reading
  state, and remove it.
- Reading state is one of `queued`, `reading`, or `finished`.
- Updating the reading state must preserve the title, author, and notes.
- Missing notes are valid and are stored as absent rather than fabricated.
- The browser page can add books, show the queue, change reading state, and
  remove books without a full page reload.
- The health endpoint is public; book operations require the configured shared
  access key.
- Data belongs to one installation; no account federation or cross-installation
  sharing is required.
