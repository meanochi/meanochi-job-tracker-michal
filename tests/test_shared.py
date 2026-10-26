"""Domain tools in shared/ - plain functions, checked against the files they write."""

import io
import json

import pytest

from shared import jobs, preferences
from shared.jobs import ToolError


def test_add_and_update_writes_status_and_history(offline):
    jobs.add_application("Wix", "Backend Developer", "https://wix.com/job")
    assert jobs.update_status("wix", "Interview") == "updated: Wix applied -> interview"
    saved = json.loads((offline / "jobs.json").read_text(encoding="utf-8"))
    assert saved[0]["status"] == "interview"
    assert [h["status"] for h in saved[0]["history"]] == ["applied", "interview"]


@pytest.mark.parametrize("call, message", [
    (lambda: jobs.add_application("", "Dev"), "required"),
    (lambda: jobs.update_status("Nobody", "offer"), "no application"),
    (lambda: jobs.search_applications("hired"), "invalid status"),
    (lambda: jobs.fetch_job_posting("ftp://x"), "http"),
])
def test_bad_input_raises_tool_error(call, message):
    with pytest.raises(ToolError, match=message):
        call()


def test_duplicate_company_is_rejected():
    jobs.add_application("Wix", "Dev")
    with pytest.raises(ToolError, match="already exists"):
        jobs.add_application("WIX", "Other")


def test_search_is_compact_and_filters():
    jobs.add_application("Wix", "Dev")
    jobs.add_application("Monday", "QA")
    jobs.update_status("Monday", "offer")
    assert jobs.search_applications("offer") == "1 applications:\n- Monday | QA | offer"
    assert jobs.search_applications("rejected") == "no applications with status rejected"


class FakeHTTPResponse(io.BytesIO):
    class headers:
        @staticmethod
        def get_content_charset():
            return "utf-8"

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_fetch_strips_html_and_truncates(monkeypatch):
    html = "<html><script>var x=1;</script><body><h1>Junior Dev</h1>" + "<p>word</p>" * 1000
    monkeypatch.setattr(jobs.urllib.request, "urlopen",
                        lambda req, timeout, context: FakeHTTPResponse(html.encode()))
    out = jobs.fetch_job_posting("https://jobs.example/1")
    assert out.startswith("Junior Dev word")
    assert "var x" not in out
    assert "[truncated" in out and len(out) < jobs.MAX_POSTING_CHARS + 50


def test_fetch_network_error_becomes_tool_error(monkeypatch):
    def boom(*a, **k):
        raise OSError("Blocked by NetFree")
    monkeypatch.setattr(jobs.urllib.request, "urlopen", boom)
    with pytest.raises(ToolError, match="NetFree"):
        jobs.fetch_job_posting("https://blocked.example")


def test_preference_overwrite_resolves_contradiction(offline):
    preferences.save_preference("work_mode", "hybrid only")
    out = preferences.save_preference("Work Mode", "hybrid or office")
    assert out == "saved: work_mode = hybrid or office (was: hybrid only)"
    assert json.loads((offline / "preferences.json").read_text()) == {"work_mode": "hybrid or office"}
