"""Stage 2: the whole agent in one file, before splitting it into harness/.

Run:  python API/scratch.py "add Wix, Backend Developer, then show all applications"
Needs ANTHROPIC_API_KEY in the environment.
"""

import sys
from pathlib import Path

import anthropic
import truststore

# NetFree's CA fails Python 3.14's strict checks; verify TLS via the Windows cert store instead.
truststore.inject_into_ssl()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared import jobs  # noqa: E402

MODEL = "claude-opus-5-5"
EFFORT = "medium"
SYSTEM = (
    "You are a job-search tracking assistant. Use the tools to record and look up "
    "applications. Keep answers short. Reply in the user's language."
)

# 1. Tool schemas: what the model sees. It never sees our Python code, only these.
TOOLS = [
    {
        "name": "add_application",
        "description": "Record a new job application (status starts as 'applied').",
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "role": {"type": "string"},
                "url": {"type": "string", "description": "Posting URL, optional"},
            },
            "required": ["company", "role"],
        },
    },
    {
        "name": "update_status",
        "description": "Change the status of an existing application.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "status": {"type": "string", "enum": list(jobs.VALID_STATUSES)},
            },
            "required": ["company", "status"],
        },
    },
    {
        "name": "search_applications",
        "description": "List applications, optionally filtered by status. Returns one line per application.",
        "input_schema": {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": list(jobs.VALID_STATUSES)}},
        },
    },
    {
        "name": "fetch_job_posting",
        "description": "Download a job posting URL and return its text (trimmed to ~1500 chars).",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
]

# 2. Dispatch: tool name -> the real Python function.
FUNCTIONS = {
    "add_application": jobs.add_application,
    "update_status": jobs.update_status,
    "search_applications": jobs.search_applications,
    "fetch_job_posting": jobs.fetch_job_posting,
}


def run_tool(block) -> dict:
    """Run one tool_use block and build its tool_result. Errors go back to the model."""
    try:
        output = FUNCTIONS[block.name](**block.input)
        return {"type": "tool_result", "tool_use_id": block.id, "content": output}
    except (jobs.ToolError, KeyError, TypeError) as e:
        return {"type": "tool_result", "tool_use_id": block.id, "content": str(e), "is_error": True}


def run(user_text: str, client=None) -> str:
    client = client or anthropic.Anthropic()
    messages = [{"role": "user", "content": user_text}]

    # 3. The loop: call the model; while it asks for tools, run them and call again.
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
            output_config={"effort": EFFORT},
        )
        u = response.usage
        print(f"[scratch] stop_reason={response.stop_reason} in={u.input_tokens} out={u.output_tokens}")

        # The assistant turn (text + tool_use blocks) must go into history as-is.
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        # ALL tool results go back together, in ONE user message.
        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"[scratch] tool {block.name}({block.input})")
                results.append(run_tool(block))
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    print(run(" ".join(sys.argv[1:]) or "Show all my applications"))
