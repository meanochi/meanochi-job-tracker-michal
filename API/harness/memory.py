"""Long-term memory: what survives between sessions, and how it is retrieved.

Where: on disk through shared/ - preferences.json (user preferences, written by the
save_preference tool) and jobs.json (applications and their statuses).

How it is retrieved (selectively, not "everything every turn"):
- preferences are small and always relevant -> loaded once per session, into its first message.
- applications can grow large -> only an overview line plus the companies the user mentions.
  Anything else the model fetches itself with search_applications.
"""

from collections import Counter

from shared import jobs, preferences

from . import log


def preferences_block() -> str:
    prefs = preferences.load_preferences()
    log(__file__, f"loaded {len(prefs)} saved preferences")
    if not prefs:
        return "No saved preferences yet."
    return "\n".join(f"- {k}: {v}" for k, v in sorted(prefs.items()))


def jobs_overview() -> str:
    all_jobs = jobs.load_jobs()
    if not all_jobs:
        return "Tracked applications: none yet."
    counts = Counter(j["status"] for j in all_jobs)
    by_status = ", ".join(f"{s} {n}" for s, n in sorted(counts.items()))
    return f"Tracked applications: {len(all_jobs)} ({by_status})."


def relevant_jobs(user_text: str) -> list[str]:
    text = user_text.lower()
    hits = [j for j in jobs.load_jobs() if j["company"].lower() in text]
    log(__file__, f"{len(hits)} mentioned companies found in memory")
    return [f"- {j['company']} | {j['role']} | {j['status']}" for j in hits]
