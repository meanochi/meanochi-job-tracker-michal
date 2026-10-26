"""The SDK agent: Claude Code runs the harness, we only configure it. One Agent = one session.

Each line that takes over the job of an API/harness/ file is marked "# replaces: <file>".
"""

import time

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, ResultMessage, ToolUseBlock

import tools
from shared import preferences
from shared.jobs import data_dir

MODEL = "claude-opus-5-5"
EFFORT = "medium"

SYSTEM_PROMPT = """You are a job-search tracking assistant.

- Use the tools to record and look up applications; never guess a status. Call search_applications whenever you need current statuses.
- When the user states a lasting preference (work mode, location, role type, salary...), save it with save_preference. If your memory (CLAUDE.md) already has a key on the same topic, reuse that key so the new value replaces the old one.
- Memory in CLAUDE.md comes from earlier sessions. A newer statement from the user overrides it.
- When the user shares a job posting URL, read it with fetch_job_posting and check it against their preferences.
- Keep answers short. Reply in the user's language."""


def write_memory_file() -> None:
    """Render preferences.json as CLAUDE.md in the agent's working directory."""
    prefs = preferences.load_preferences()  # replaces: memory.py (retrieval)
    lines = [f"- {k}: {v}" for k, v in sorted(prefs.items())] or ["No saved preferences yet."]  # replaces: memory.py
    data_dir().mkdir(parents=True, exist_ok=True)
    (data_dir() / "CLAUDE.md").write_text("# Saved preferences\n" + "\n".join(lines) + "\n", encoding="utf-8")  # replaces: memory.py


class Agent:
    def __init__(self, session_id: str | None = None):
        write_memory_file()  # replaces: memory.py (loaded once per session, like the API's frozen system prompt)
        self.options = ClaudeAgentOptions(
            model=MODEL,
            effort=EFFORT,
            system_prompt=SYSTEM_PROMPT,  # replaces: context.py (our own prompt, not Claude Code's default)
            tools=[],  # replaces: context.py (no built-in tools in the prompt)
            mcp_servers={tools.SERVER: tools.server},  # replaces: tools.py
            allowed_tools=tools.ALLOWED,  # replaces: tools.py
            strict_mcp_config=True,  # replaces: tools.py (ignore any other MCP config on this machine)
            setting_sources=["project"],  # replaces: memory.py (loads CLAUDE.md from cwd)
            cwd=str(data_dir()),  # replaces: memory.py + history.py (project dir = data dir)
            resume=session_id,  # replaces: history.py (Claude Code stores the transcript itself)
            max_turns=12,  # replaces: loop.py (MAX_MODEL_CALLS)
        )
        # loop.py, compaction.py and caching.py have no line here: Claude Code does them automatically.
        self.client = ClaudeSDKClient(self.options)
        self.session_id = session_id
        self._session_cost = 0.0  # replaces: tokens.py

    async def __aenter__(self):
        await self.client.connect()
        return self

    async def __aexit__(self, *exc):
        await self.client.disconnect()

    async def ask(self, user_text: str) -> dict:
        t0 = time.perf_counter()
        await self.client.query(user_text)  # replaces: loop.py
        reply, used, calls, usage, cost = "", [], set(), {}, 0.0
        async for msg in self.client.receive_response():  # replaces: loop.py
            if isinstance(msg, AssistantMessage):
                calls.add(msg.message_id)  # replaces: tokens.py (model calls)
                used += [b.name.removeprefix(f"mcp__{tools.SERVER}__")  # replaces: tokens.py (tools used)
                         for b in msg.content if isinstance(b, ToolUseBlock)]  # replaces: tokens.py
            elif isinstance(msg, ResultMessage):
                self.session_id = msg.session_id  # replaces: history.py
                reply = msg.result or ""  # replaces: loop.py (final text)
                if msg.is_error:  # e.g. expired login, API error: say so instead of looking like a reply
                    reply = f"ERROR ({msg.subtype}): {reply or msg.errors}"
                    print(f"[agent.py] {reply}", flush=True)
                usage = msg.usage or {}  # replaces: tokens.py
                total = msg.total_cost_usd or 0.0  # replaces: tokens.py (cumulative for the whole session)
                cost, self._session_cost = total - self._session_cost, total  # replaces: tokens.py (per turn)
        turn = {  # replaces: tokens.py
            "input": usage.get("input_tokens", 0),  # replaces: tokens.py
            "cache_read": usage.get("cache_read_input_tokens", 0),  # replaces: tokens.py
            "cache_write": usage.get("cache_creation_input_tokens", 0),  # replaces: tokens.py
            "output": usage.get("output_tokens", 0),  # replaces: tokens.py
            "model_calls": len(calls),  # replaces: tokens.py
            "tools": used,  # replaces: tokens.py
            "cost_usd": round(cost, 6),  # replaces: tokens.py
            "seconds": round(time.perf_counter() - t0, 2),  # replaces: tokens.py
        }  # replaces: tokens.py
        prompt = turn["input"] + turn["cache_read"] + turn["cache_write"]  # replaces: tokens.py
        turn["cache_hit_pct"] = round(100 * turn["cache_read"] / prompt, 1) if prompt else 0.0  # replaces: tokens.py
        print(f"[agent.py] turn: {turn['model_calls']} calls, tools={used}, "
              f"cache {turn['cache_hit_pct']}%, ${turn['cost_usd']:.4f}", flush=True)
        return {"reply": reply, **turn}
