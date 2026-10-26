"""Domain tools for the job tracker - plain Python, no AI.

Both harnesses (API/ and SDK/) wrap these same functions.
Errors are raised as ToolError; each harness turns them into is_error results.
Outputs are short strings on purpose (token optimization).
"""

import json
import os
import re
import ssl
import urllib.request
from datetime import date
from html import unescape
from pathlib import Path

import truststore

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VALID_STATUSES = ("saved", "applied", "interview", "offer", "rejected", "withdrawn")
MAX_POSTING_CHARS = 1500


class ToolError(Exception):
    """An error the model should see and can recover from."""


def data_dir() -> Path:
    # JOB_TRACKER_DIR lets tests and scenario runs use a clean, separate directory.
    return Path(os.environ.get("JOB_TRACKER_DIR", PROJECT_ROOT / "data"))


def data_path() -> Path:
    return data_dir() / "jobs.json"


def load_jobs() -> list[dict]:
    path = data_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_jobs(jobs: list[dict]) -> None:
    path = data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")


def _find(jobs: list[dict], company: str) -> dict | None:
    key = company.strip().lower()
    return next((j for j in jobs if j["company"].lower() == key), None)


def add_application(company: str, role: str, url: str = "") -> str:
    company, role = company.strip(), role.strip()
    if not company or not role:
        raise ToolError("company and role are required")
    jobs = load_jobs()
    if _find(jobs, company):
        raise ToolError(f"{company} already exists; use update_status instead")
    today = date.today().isoformat()
    jobs.append({
        "company": company,
        "role": role,
        "url": url.strip(),
        "status": "applied",
        "history": [{"status": "applied", "date": today}],
    })
    _save_jobs(jobs)
    return f"added: {company} | {role} | applied"


def update_status(company: str, status: str) -> str:
    status = status.strip().lower()
    if status not in VALID_STATUSES:
        raise ToolError(f"invalid status '{status}'; use one of: {', '.join(VALID_STATUSES)}")
    jobs = load_jobs()
    job = _find(jobs, company)
    if job is None:
        raise ToolError(f"no application for '{company}'")
    old = job["status"]
    job["status"] = status
    job["history"].append({"status": status, "date": date.today().isoformat()})
    _save_jobs(jobs)
    return f"updated: {job['company']} {old} -> {status}"


def search_applications(status: str | None = None) -> str:
    jobs = load_jobs()
    if status:
        status = status.strip().lower()
        if status not in VALID_STATUSES:
            raise ToolError(f"invalid status '{status}'; use one of: {', '.join(VALID_STATUSES)}")
        jobs = [j for j in jobs if j["status"] == status]
    if not jobs:
        return "no applications" + (f" with status {status}" if status else "")
    lines = [f"- {j['company']} | {j['role']} | {j['status']}" for j in jobs]
    return f"{len(jobs)} applications:\n" + "\n".join(lines)


def _html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", html)
    text = unescape(re.sub(r"(?s)<[^>]+>", " ", html))
    return re.sub(r"\s+", " ", text).strip()


def fetch_job_posting(url: str) -> str:
    """External tool: download a posting and return a trimmed plain-text version."""
    if not url.startswith(("http://", "https://")):
        raise ToolError("url must start with http:// or https://")
    req = urllib.request.Request(url, headers={"User-Agent": "job-tracker/1.0"})
    # Verify TLS with the OS certificate store (Python's own CA checks reject some local CAs).
    ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            raw = resp.read(500_000)
            charset = resp.headers.get_content_charset() or "utf-8"
    except Exception as e:  # network errors go back to the model, not up the stack
        raise ToolError(f"fetch failed: {e}") from e
    text = _html_to_text(raw.decode(charset, errors="replace"))
    if len(text) > MAX_POSTING_CHARS:
        text = text[:MAX_POSTING_CHARS] + f" ...[truncated, {len(text)} chars total]"
    return text or "empty page"
