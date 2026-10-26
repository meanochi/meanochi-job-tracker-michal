"""Tools: JSON schemas the model sees, dispatch to shared/ functions, errors back as is_error."""

import json

from shared import jobs, preferences

from . import log

MAX_RESULT_CHARS = 2000  # guard so no single tool result can flood the context

STATUS_ENUM = list(jobs.VALID_STATUSES)

SCHEMAS = [
    {
        "name": "add_application",
        "description": "Record a new job application. Its status starts as 'applied'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "role": {"type": "string"},
                "url": {"type": "string", "description": "Posting URL, if known"},
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
                "status": {"type": "string", "enum": STATUS_ENUM},
            },
            "required": ["company", "status"],
        },
    },
    {
        "name": "search_applications",
        "description": "List tracked applications, one line each, optionally filtered by status.",
        "input_schema": {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": STATUS_ENUM}},
        },
    },
    {
        "name": "fetch_job_posting",
        "description": "Download a job posting URL and return its plain text, trimmed to ~1500 characters.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "name": "save_preference",
        "description": (
            "Save a lasting job-search preference to long-term memory. One value per key: "
            "saving an existing key replaces its value. Prefer short keys such as "
            "work_mode, location, role_type, min_salary."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["key", "value"],
        },
    },
]

FUNCTIONS = {
    "add_application": jobs.add_application,
    "update_status": jobs.update_status,
    "search_applications": jobs.search_applications,
    "fetch_job_posting": jobs.fetch_job_posting,
    "save_preference": preferences.save_preference,
}


def run_tool(name: str, args: dict, tool_use_id: str) -> dict:
    is_error = True
    if name not in FUNCTIONS:
        output = f"unknown tool '{name}'"
    else:
        try:
            output = FUNCTIONS[name](**args)
            is_error = False
        except jobs.ToolError as e:
            output = str(e)
        except TypeError as e:  # wrong or missing arguments
            output = f"bad arguments: {e}"
        except Exception as e:  # a bug in a tool must not crash the agent
            output = f"{type(e).__name__}: {e}"
    if len(output) > MAX_RESULT_CHARS:
        output = output[:MAX_RESULT_CHARS] + " ...[truncated]"
    status = "ERROR " if is_error else ""
    log(__file__, f"{name}({json.dumps(args, ensure_ascii=False)}) -> {status}{output[:100]!r}")
    result = {"type": "tool_result", "tool_use_id": tool_use_id, "content": output}
    if is_error:
        result["is_error"] = True
    return result


def run_all(tool_uses: list[dict]) -> list[dict]:
    """Run every tool_use block of one assistant turn; the caller sends all results in ONE message."""
    return [run_tool(b["name"], b["input"], b["id"]) for b in tool_uses]
