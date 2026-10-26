"""The scenario runner end to end on the API agent with a scripted fake model."""

import json

from agent import Agent
from conftest import ROOT, FakeClient, response, text, tool
from harness import tools
from shared.scenario import count_loc, run_scenario


def scripted_model():
    return FakeClient(
        # session 1
        response("tool_use", tool("1", "add_application", company="Wix", role="Backend Developer"),
                 tool("2", "add_application", company="Monday.com", role="Full-Stack Junior")),
        response("end_turn", text("Added both.")),
        response("tool_use", tool("3", "save_preference", key="work_mode", value="hybrid only")),
        response("end_turn", text("Saved.")),
        response("tool_use", tool("4", "update_status", company="Wix", status="interview")),
        response("end_turn", text("Good luck!")),
        response("tool_use", tool("5", "fetch_job_posting", url="https://www.python.org/jobs/")),
        response("end_turn", text("Mostly senior Python roles.")),
        # session 2
        response("end_turn", text("You want hybrid jobs; Wix is at the interview stage.")),
        response("tool_use", tool("6", "save_preference", key="work_mode", value="hybrid or full-time office")),
        response("end_turn", text("Updated.")),
        response("tool_use", tool("7", "update_status", company="Monday.com", status="rejected")),
        response("end_turn", text("Wix is still active.")),
    )


def test_scenario_runs_both_sessions_and_all_checks_pass(tmp_path, monkeypatch):
    monkeypatch.setitem(tools.FUNCTIONS, "fetch_job_posting", lambda url: "Python jobs board")
    model, agents = scripted_model(), []

    def run_session(prompts):
        agents.append(Agent(client=model))  # new instance per session
        return [agents[-1].ask(p) for p in prompts]

    out = tmp_path / "api.json"
    results = run_scenario(str(ROOT / "scenario.json"), str(out), "api", run_session, runs_dir=tmp_path)

    assert len(agents) == 2 and agents[0].session_id != agents[1].session_id
    assert results["checks_passed"] == "6/6", results["checks"]
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert len(saved["turns"]) == 7 and [t["session"] for t in saved["turns"]] == [1, 1, 1, 1, 2, 2, 2]
    for key in ["input", "cache_read", "cache_write", "output", "model_calls", "tools", "cost_usd", "seconds"]:
        assert key in saved["turns"][0]
    assert saved["totals"]["model_calls"] == 13


def test_failed_state_is_reported_as_fail(tmp_path, monkeypatch):
    monkeypatch.setitem(tools.FUNCTIONS, "fetch_job_posting", lambda url: "Python jobs board")
    model = FakeClient(*[response("end_turn", text("ok")) for _ in range(7)])  # never calls a tool

    def run_session(prompts):
        agent = Agent(client=model)
        return [agent.ask(p) for p in prompts]

    results = run_scenario(str(ROOT / "scenario.json"), str(tmp_path / "x.json"), "api", run_session,
                           runs_dir=tmp_path)
    assert results["checks_passed"] == "0/6"


def test_loc_counts_every_harness_part():
    loc = count_loc()
    assert all(loc["api"][p] > 0 for p in loc["api"])
    assert loc["sdk"]["caching"] == 0 and loc["sdk"]["compaction"] == 0  # done by Claude Code
    assert loc["sdk"]["tools"] > 0 and loc["sdk"]["tokens"] > 0
