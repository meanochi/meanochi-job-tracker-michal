"""The same shared/ functions, exposed to Claude Code as an in-process MCP server."""

from typing import Annotated

from claude_agent_sdk import create_sdk_mcp_server, tool

from shared import jobs, preferences

SERVER = "jobs"
STATUSES = ", ".join(jobs.VALID_STATUSES)


def _run(fn, **kwargs) -> dict:  # replaces: tools.py (dispatch)
    try:  # replaces: tools.py
        return {"content": [{"type": "text", "text": fn(**kwargs)}]}  # replaces: tools.py
    except jobs.ToolError as e:  # replaces: tools.py (errors back as is_error)
        return {"content": [{"type": "text", "text": str(e)}], "is_error": True}  # replaces: tools.py


@tool("add_application", "Record a new job application. Its status starts as 'applied'.",  # replaces: tools.py
      {"company": str, "role": str, "url": Annotated[str, "Posting URL, empty if unknown"]})  # replaces: tools.py
async def add_application(args):  # replaces: tools.py
    return _run(jobs.add_application, **args)  # replaces: tools.py


@tool("update_status", f"Change the status of an existing application. Status: {STATUSES}.",  # replaces: tools.py
      {"company": str, "status": str})  # replaces: tools.py
async def update_status(args):  # replaces: tools.py
    return _run(jobs.update_status, **args)  # replaces: tools.py


@tool("search_applications", "List tracked applications, one line each, optionally filtered by status.",  # replaces: tools.py
      {"type": "object", "properties": {"status": {"type": "string", "enum": list(jobs.VALID_STATUSES)}}})  # replaces: tools.py
async def search_applications(args):  # replaces: tools.py
    return _run(jobs.search_applications, **args)  # replaces: tools.py


@tool("fetch_job_posting", "Download a job posting URL and return its plain text, trimmed to ~1500 characters.",  # replaces: tools.py
      {"url": str})  # replaces: tools.py
async def fetch_job_posting(args):  # replaces: tools.py
    return _run(jobs.fetch_job_posting, **args)  # replaces: tools.py


@tool("save_preference",  # replaces: tools.py + memory.py (where memory is written)
      "Save a lasting job-search preference to long-term memory. One value per key: saving an "  # replaces: tools.py + memory.py
      "existing key replaces its value. Prefer short keys such as work_mode, location, role_type, min_salary.",  # replaces: tools.py + memory.py
      {"key": str, "value": str})  # replaces: tools.py + memory.py
async def save_preference(args):  # replaces: tools.py + memory.py
    return _run(preferences.save_preference, **args)  # replaces: tools.py + memory.py


ALL = [add_application, update_status, search_applications, fetch_job_posting, save_preference]  # replaces: tools.py
server = create_sdk_mcp_server(SERVER, tools=ALL)  # replaces: tools.py (schemas the model sees)
ALLOWED = [f"mcp__{SERVER}__{t.name}" for t in ALL]  # replaces: tools.py (restricted tool list)
