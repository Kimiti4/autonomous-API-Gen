"""Semantic Git History -- ledger-mapped commits."""
def semantic_commits(ledger_events):
    mapping = {"feat:": "feature", "fix:": "fix", "security:": "security"}
    commits = []
    for ev in ledger_events:
        prefix = "feat:" if "feat" in ev.event_id else "chore:"
        commits.append(f"{prefix} {ev.event_id} -- {ev.payload.get('verdict','')}")
    return tuple(commits)
