"""What the model sees in each turn.

- system: static instructions only - identical in every session, so tools + system are read
  from the prompt cache even at the start of a new session. It is also frozen per session
  (stored in history): editing it mid-session would invalidate the cache and Opus 5.5's
  preserved thinking.
- first user turn of a session: a <memory> block with the saved preferences. Preferences
  saved later in the session reach the model through the save_preference tool result.
- each user turn: a small <context> block (overview + statuses of the companies mentioned)
  followed by the user's text. Everything is appended once and never edited.
- the full application list is NOT sent; the model calls search_applications when needed.
"""

from . import log, memory

INSTRUCTIONS = """You are a job-search tracking assistant.

- Use the tools to record and look up applications; never guess a status. Each user message starts with a <context> block holding current facts for the companies it mentions; call search_applications for anything else.
- The first user message of a session also starts with a <memory> block: preferences saved in earlier sessions. A newer statement from the user overrides it.
- When the user states a lasting preference (work mode, location, role type, salary...), save it with save_preference. If <memory> already has a key on the same topic, reuse that key so the new value replaces the old one.
- When the user shares a job posting URL, read it with fetch_job_posting and check it against their preferences.
- Keep answers short. Reply in the user's language."""


def build_system() -> list[dict]:
    log(__file__, f"built system prompt ({len(INSTRUCTIONS)} chars, same for every session)")
    return [{"type": "text", "text": INSTRUCTIONS}]


def build_user_turn(user_text: str, first_in_session: bool = False) -> dict:
    facts = [memory.jobs_overview(), *memory.relevant_jobs(user_text)]
    content = [
        {"type": "text", "text": "<context>\n" + "\n".join(facts) + "\n</context>"},
        {"type": "text", "text": user_text},
    ]
    if first_in_session:
        prefs = f"<memory>\nSaved preferences:\n{memory.preferences_block()}\n</memory>"
        content.insert(0, {"type": "text", "text": prefs})
    log(__file__, f"user turn + {len(facts)} context lines" + (" + memory" if first_in_session else ""))
    return {"role": "user", "content": content}
