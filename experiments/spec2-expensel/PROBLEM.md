# ExpenseLedger: keep spending accountable.

ExpenseLedger helps a small business keep its spending accountable. Claims live
in named vendors. Every claim carries a title, optional notes, an amount in
decimal numbers, a status that moves from draft to submitted to approved or
rejected, an optional expense date, and a category chosen from meals, travel,
lodging or supplies. Everything is reachable from a simple web page that talks
to a small service over plain HTTP using a shared access key.

## Expected behavior

- Creating a claim records its title, notes, amount, status, expense date,
  category, and optional vendor membership, and makes it immediately fetchable.
- Listing claims returns every claim; fetching one claim returns exactly that
  claim.
- Approving a claim and later rejecting it changes only the status: amount,
  category, notes, expense date, and vendor membership are retained.
- Deleting a claim removes it; a later fetch reports it as unknown.
- A claim created without an expense date is valid and stores no expense date.
- Claims can belong to a named vendor; fetching the claim shows which vendor it
  is in.
- When an access key is configured, requests without it are rejected with a 401
  response; the liveness endpoint at /health stays open and reports ok.
- The browser page lists claims, creates them, updates their status, and deletes
  them without reloading the page.

## Notes

- Data is per installation; there is no cross-installation sharing.
- The system must remain understandable to a single maintainer.
